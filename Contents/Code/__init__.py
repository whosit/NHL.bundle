import calendar

# Borrows heavily from the XBMC NHL GameCenter Add-on by Carb0 - http://forum.xbmc.org/showthread.php?tid=118853

Login = SharedCodeService.gamecenter.GCLogin

ARCHIVE_XML     = 'http://gamecenter.nhl.com/nhlgc/servlets/allarchives'
GAMES_XML       = 'http://gamecenter.nhl.com/nhlgc/servlets/archives'
VAULT_XML       = 'http://nhl.cdn.neulion.net/u/nhlgc/flex/vault.xml'
TODAY_GAMES     = 'http://live.nhle.com/GameData/GCScoreboard/%s.jsonp'

GAME_URL        = 'http://www.nhl.com/ice/gamecenterlive.htm?id=%s'

VAULT_NAMESPACES = {
    "xmlns"     :       "urn:schemas-microsoft-com:office:spreadsheet",
    "o"         :       "urn:schemas-microsoft-com:office:office",
    "x"         :       "urn:schemas-microsoft-com:office:excel",
    "ss"        :       "urn:schemas-microsoft-com:office:spreadsheet",
    "html"      :       "http://www.w3.org/TR/REC-html40"
    }

ONE_HOUR        = 60 * 60
ONE_DAY         = ONE_HOUR * 24
ONE_WEEK        = ONE_DAY * 7
ONE_MONTH       = ONE_DAY * 30
####################################################################################################
PREFIX  = "/video/nhl"
NAME    = L("NHL")
ART     = 'art-default.jpg'
ICON    = 'icon-default.png'
NHL     = 'nhl.png'
####################################################################################################

def Start():
    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    DirectoryObject.thumb = R(NHL)
    DirectoryObject.art = R(ART)
    VideoClipObject.thumb= R(ICON)

def ValidatePrefs():
    ## do some checks and return a
    ## message container
    if( Prefs['gc_username'] and Prefs['gc_password'] ):
        Dict['cookies'] = Login(Prefs['gc_username'], Prefs['gc_password'])
        Log("Login succeeded")
    else:
        Log("Login failed")
        return ObjectContainer(
            header=L("Error"),
            message=L("You need to provide a valid username and password. Please buy a subscription.")
        )

@handler(PREFIX, NAME)
def MainMenu():    
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(LiveGames), title="Live Games"))
    oc.add(DirectoryObject(key=Callback(ArchiveGames, condensed=True), title=L("Condensed Games")))
    oc.add(DirectoryObject(key=Callback(ArchiveGames), title=L("Archived Games")))
    oc.add(DirectoryObject(key=Callback(ClassicGames), title=L("Classic Games")))
    oc.add(PrefsObject(title=L("Preferences")))
    return oc

@route(PREFIX + '/live')
def LiveGames():
    oc = ObjectContainer(title2=L("Live Games"), no_cache=True)
    today = Datetime.Now().date()
    content = HTTP.Request(TODAY_GAMES % today).content
    # we need to clean the string before parsing it as json
    json_string = content.split('(',1)[1].split(')',1)[0]
    games_json = JSON.ObjectFromString(json_string)
    for game in games_json['games']:
        game_id     = game['id']
	url = GAME_URL % game_id
        homeTeam    = game['hta']
        awayTeam    = game['ata']
        gameTime    = game['bs']
        title = title = "%s at %s" % (awayTeam, homeTeam)
	summary = ""
        if game['bsc'] == "final":
            if Prefs['score_summary']:
                summary = "%s - %s %s" % (game['ats'], game['hts'], gameTime)
	    title = title + " FINAL"
            oc.add(DirectoryObject(key=Callback(HomeOrAway, url=url, title=title, summary=summary, date=today), title=title, summary=summary))
        elif game['bsc'] in ["progress","critical"]:
            title = "%s %s ET" % (title, gameTime)
            ''' handle games which are just starting and those that have been running a while but not ended '''
            oc.add(DirectoryObject(key=Callback(HomeOrAway, url=url+"#LIVE", title=title, summary=summary, date=today), title=title, summary=summary))
    return oc

@route(PREFIX + '/archive', condensed=bool)
def ArchiveGames(condensed=False):
    oc = ObjectContainer(title2=L("Archived Games"))
    data = GetXML(url=ARCHIVE_XML, values={'date' : 'true', 'isFlex' : 'true'}, cache_length=ONE_DAY)
    seasons = data.xpath('//season')
    seasons.reverse()
    current_season = seasons[0].get('id')
    current_month = Datetime.Now().month
    oc.add(DirectoryObject(key=Callback(Games, season=current_season, month=current_month, condensed=condensed), title=L("Most Recent Games")))
    for entry in seasons:
        season = entry.get('id')
        if int(season) < 2010:
            ''' links for seasons older than this don't work, so we'll ignore them '''
            continue
        oc.add(DirectoryObject(key=Callback(Months, season=season, condensed=condensed), title=season + L(" Season")))
    return oc

@route(PREFIX + '/classic')
def ClassicGames():
    oc = ObjectContainer(title2=L("Classic Games"))
    filters = [L("Decade"), L("Team"), L("Key Players"), L("Category")]
    oc.add(DirectoryObject(key=Callback(UnfilteredClassics), title=L("All Classic Games")))
    for option in filters:
        oc.add(DirectoryObject(key=Callback(FilteredClassics, option=option), title=L("Filter by ") + option))
    return oc

'''
Class Games XML Map
Row => Game
Cell[0]/Data[0].text => date
Cell[1]/Data[0].text + Cell[2]/Data[0].text => Team1
Cell[3]/Data[0].text => Team1 Score
Cell[4]/Data[0].text + Cell[5]/Data[0].text => Team2
Cell[6]/Data[0].text => Team2 Score
Cell[7]/Data[0].text => title
Cell[8]/Data[0].text => summary
Cell[9]/Data[0].text => category
Cell[10]Data[0].text => ???
Cell[11]Data[0].text => lo_res feed
Cell[12]Data[0].text => hi_res feed
Cell[13]/Data[0].text => key player(s)
'''

@route(PREFIX + '/unfilteredclassics', offset=int)
def UnfilteredClassics(offset=0):
    oc = ObjectContainer(title2=L("Classic Games"))
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    i=offset
    new_offset = offset + 20
    while i < new_offset:
        game = data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)[i]
        date = game.xpath('./ss:Cell/ss:Data', namespaces=VAULT_NAMESPACES)[0].text
        title = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[7].text
        summary = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[8].text
        thumb = 'http://nhl.cdn.neulion.net/u/nhl/thumbs/vault/' + game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text[:-3] + 'jpg'
        lo_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text
        hi_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[12].text
        oc.add(CreateClassicVideo(title=title, summary=summary, thumb=thumb, date=date, lo_res=lo_res, hi_res=hi_res))
        i += 1
    if offset < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
        oc.add(NextPageObject(key=Callback(UnfilteredClassics, offset=new_offset)))
    return oc

@route(PREFIX + '/filteredclassics')
def FilteredClassics(option):
    oc = ObjectContainer(title2=L("Classic Games"))
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    Decades = [
        {"title" : "1960s", "range" : ["1960","1969"]},
        {"title" : "1970s", "range" : ["1970","1979"]},
        {"title" : "1980s", "range" : ["1980","1989"]},
        {"title" : "1990s", "range" : ["1990","1999"]},
        {"title" : "2000s", "range" : ["2000","2013"]}
        ]
    if option == L("Decade"):
        for decade in Decades:
            oc.add(DirectoryObject(key=Callback(ClassicsDecades, decade=decade['range']), title=decade['title']))
    elif option == L("Team"):
        teams = []
        for game in data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES):
            team1_city = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[1].text.strip()
            team1_name = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[2].text.strip()
            team1 = "%s %s" % (team1_city, team1_name)
            if team1 not in teams:
                teams.append(team1)
                oc.add(DirectoryObject(key=Callback(ClassicsTeams, team=team1), title=team1))
	    team2_city = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[4].text.strip()
            team2_name = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[5].text.strip()
            team2 = "%s %s" % (team2_city, team2_name)
            if team2 not in teams:
                teams.append(team2)
                oc.add(DirectoryObject(key=Callback(ClassicsTeams, team=team2), title=team2))
    elif option == L("Key Players"):
        players = []
        for game in data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES):
            try:
		key_players = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[13].text
		for player in key_players.split(','):
		    player = player.strip()
		    if player not in players:
			players.append(player)
			oc.add(DirectoryObject(key=Callback(ClassicsPlayers, player=player), title=player))
	    except:
		continue
    elif option == L("Category"):
        categories = []
        for game in data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES):
            category = game.xpath('./ss:Cell/ss:Data', namespaces=VAULT_NAMESPACES)[9].text
            if category not in categories:
                categories.append(category)
                oc.add(DirectoryObject(key=Callback(ClassicsCategories, category=category), title=category))
    oc.objects.sort(key = lambda obj: obj.title)
    return oc

@route(PREFIX + '/classicsdecades', decade=list, offset=int)
def ClassicsDecades(decade, offset=0):
    oc = ObjectContainer(title2=L("Classic Games"))
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    i=offset
    count = 0
    while count < 10 and i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
	game = data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)[i]
	i = i +1
        date = game.xpath('./ss:Cell/ss:Data', namespaces=VAULT_NAMESPACES)[0].text
	year = Datetime.ParseDate(date).year
	if year in range(int(decade[0]),int(decade[1])):
	    title = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[7].text
	    summary = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[8].text
	    thumb = 'http://nhl.cdn.neulion.net/u/nhl/thumbs/vault/' + game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text[:-3] + 'jpg'
	    lo_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text
	    hi_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[12].text
	    oc.add(CreateClassicVideo(title=title, summary=summary, thumb=thumb, date=date, lo_res=lo_res, hi_res=hi_res))
	    count = count + 1
	else:
	    continue
    if i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
        oc.add(NextPageObject(key=Callback(ClassicsDecades, decade=decade, offset=i)))
    return oc

@route(PREFIX + '/classicsteams', offset=int)
def ClassicsTeams(team, offset=0):
    oc = ObjectContainer(title2=L("Classic Games"))
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    i=offset
    count = 0
    while count < 10 and i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
	game = data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)[i]
	teams = []
	i = i +1
        team1_city = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[1].text.strip()
        team1_name = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[2].text.strip()
        team1 = "%s %s" % (team1_city, team1_name)
        teams.append(team1)
	team2_city = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[4].text.strip()
        team2_name = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[5].text.strip()
        team2 = "%s %s" % (team2_city, team2_name)
        teams.append(team2)
	if team in teams:
	    date = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[0].text
	    title = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[7].text
	    summary = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[8].text
	    thumb = 'http://nhl.cdn.neulion.net/u/nhl/thumbs/vault/' + game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text[:-3] + 'jpg'
	    lo_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text
	    hi_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[12].text
	    oc.add(CreateClassicVideo(title=title, summary=summary, thumb=thumb, date=date, lo_res=lo_res, hi_res=hi_res))
	    count = count + 1
	else:
	    continue
    if i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
        oc.add(NextPageObject(key=Callback(ClassicsTeams, team=team, offset=i)))
    return oc

@route(PREFIX + '/classicsplayers', offset=int)
def ClassicsPlayers(player, offset=0):
    oc = ObjectContainer(title2=L("Classic Games"))
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    i=offset
    count = 0
    while count < 10 and i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
	game = data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)[i]
	i = i +1
	try:
	    players = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[13].text	    
	    if player in players:
	        date = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[0].text
	        title = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[7].text
	        summary = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[8].text
	        thumb = 'http://nhl.cdn.neulion.net/u/nhl/thumbs/vault/' + game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text[:-3] + 'jpg'
	        lo_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text
	        hi_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[12].text
	        oc.add(CreateClassicVideo(title=title, summary=summary, thumb=thumb, date=date, lo_res=lo_res, hi_res=hi_res))
	        count = count + 1
	    else:
	        continue
	except:
	    continue
    if i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
        oc.add(NextPageObject(key=Callback(ClassicsPlayers, player=player, offset=i)))
    return oc

@route(PREFIX + '/classicscategories', offset=int)
def ClassicsCategories(category, offset=0):
    oc = ObjectContainer(title2=L("Classic Games"))
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    i=offset
    count = 0
    while count < 10 and i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
	game = data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)[i]
	i = i +1
	game_category = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[9].text
	if category == game_category:
	    date = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[0].text
	    title = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[7].text
	    summary = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[8].text
	    thumb = 'http://nhl.cdn.neulion.net/u/nhl/thumbs/vault/' + game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text[:-3] + 'jpg'
	    lo_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[11].text
	    hi_res = game.xpath('.//ss:Data', namespaces=VAULT_NAMESPACES)[12].text
	    oc.add(CreateClassicVideo(title=title, summary=summary, thumb=thumb, date=date, lo_res=lo_res, hi_res=hi_res))
	    count = count + 1
	else:
	    continue
    if i < len(data.xpath('//ss:Row', namespaces=VAULT_NAMESPACES)):
        oc.add(NextPageObject(key=Callback(ClassicsCategories, category=category, offset=i)))
    return oc

@route(PREFIX + '/classicsvideo')
def CreateClassicVideo(title, summary, thumb, date, lo_res, hi_res, include_container=False):
    videoclip_obj = VideoClipObject(
        key = Callback(CreateClassicVideo, title=title, summary=summary, thumb=thumb, date=date,
            lo_res=lo_res, hi_res=hi_res, include_container=True),
        rating_key = thumb,
        title = title,
        thumb=thumb,
        summary = summary,
        originally_available_at = Datetime.ParseDate(date.replace("+"," ")).date(),
        items = [
            MediaObject(
                parts = [
                PartObject(
                    key=RTMPVideoURL(Callback(PlayClassicVideo, path=hi_res)),
                    streams=[AudioStreamObject(language_code=Locale.Language.English)]
                )
            ],
            video_codec = VideoCodec.H264,
            audio_codec = AudioCodec.AAC,
            video_resolution = '540',
            bitrate = '1600',
            optimized_for_streaming = True
            ),
            MediaObject(
                parts = [
                PartObject(
                    key=RTMPVideoURL(Callback(PlayClassicVideo, path=lo_res)),
                    streams=[AudioStreamObject(language_code=Locale.Language.English)]
                    )
                ],
            video_codec = VideoCodec.H264,
            audio_codec = AudioCodec.AAC,
            video_resolution = '360',
            bitrate = '800',
            optimized_for_streaming = True
            )
        ]
    )

    if include_container:
        return ObjectContainer(objects=[videoclip_obj])
    else:
        return videoclip_obj

@indirect
@route(PREFIX + '/playclassicvideo')
def PlayClassicVideo(path):
    values = {'isFlex' : 'true', 'type' : 'fvod', 'path' : 'rtmp://neulionms.fcod.llnwd.net/a5306/e4/mp4:s/nhl/svod/flv/vault/%s' % path}
    data = GetXML(url='http://gamecenter.nhl.com/nhlgc/servlets/encryptvideopath', values=values)
    playpath = 'mp4:' + data.xpath('//path')[0].text.split('mp4:')[1]
    rtmp_url = 'rtmp://neulionms.fcod.llnwd.net/a5306/e4/'
    return IndirectResponse(VideoClipObject, key=RTMPVideoURL(url=rtmp_url, clip=playpath))

@route(PREFIX + '/months', condensed=bool)
def Months(season, condensed=False):
    oc = ObjectContainer(title1=L("Archived Games"), title2=season + L(" Season"))
    data = GetXML(url=ARCHIVE_XML, values={'date' : 'true', 'isFlex' : 'true'}, cache_length=ONE_DAY)
    season_dates = data.xpath('//season[@id="'+season+'"]')[0].xpath('./g')
    months = []
    for entry in reversed(season_dates):
        month = entry.text.split('/')[0]
        if not month in months:
            months.append(month)
            title =  L(calendar.month_name[int(month)]) + L(" Games")
            oc.add(DirectoryObject(key=Callback(Games, season=season, month=month, condensed=condensed), title=title))
    if len(oc) < 1:
	return ObjectContainer(header=L("Empty"), message=L("No content found."))
    else:
	return oc

@route(PREFIX + '/games', condensed=bool)
def Games(season, month, condensed=False):
    oc = ObjectContainer(title1="%s/%s" % (season, month), title2="Games")
    if condensed:
        values = {'season' : season, 'isFlex' : 'true', 'month' : month, 'condensed' : 'true'}
    else:
        values = {'season' : season, 'isFlex' : 'true', 'month' : month}
    data = GetXML(url=GAMES_XML, values=values, cache_length=ONE_HOUR)
    games = data.xpath('//game')
    
    for game in games:
        game_id = game.xpath("./id")[0].text
        date = Datetime.ParseDate(game.xpath("./date")[0].text).date()
        gctype = game.xpath('./type')[0].text
        homeTeam = game.xpath("./homeTeam")[0].text
        homeGoals = game.xpath("./homeGoals")[0].text
        awayTeam = game.xpath("./awayTeam")[0].text
        awayGoals = game.xpath("./awayGoals")[0].text
        result = game.xpath("./result")[0].text
        
        title = "%s at %s - %s" % (awayTeam, homeTeam, date)
        full_game_id = '%s0%s%s' % (season, gctype, game_id)
        url = GAME_URL % full_game_id
        if condensed:
            url = url + "#CONDENSED"
        if Prefs['score_summary']:
            summary = "%s - %s %s" % (awayGoals, homeGoals, result)
        else:
            summary = None
        oc.add(DirectoryObject(key=Callback(HomeOrAway, url=url, title=title, summary=summary, date=date), title=title, summary=summary))
    if len(oc) < 1:
	return ObjectContainer(header=L("Empty"), message=L("No content found."))
    else:
	return oc

@route(PREFIX + '/homeoraway')
def HomeOrAway(url, title, summary, date):
    oc = ObjectContainer(title2=L("Choose Feed"))
    date = Datetime.ParseDate(date).date()
    if summary == "None":
	summary = ""
    oc.add(VideoClipObject(url=url+"#HOME", title=L("Home Feed"), summary="%s\n%s" % (title, summary), originally_available_at=date))
    oc.add(VideoClipObject(url=url+"#AWAY", title=L("Away Feed"), summary="%s\n%s" % (title, summary), originally_available_at=date))
    return oc

@route(PREFIX + '/getxml', values=dict, cache_length=int)
def GetXML(url, values, cache_length=ONE_DAY):
    xml_data = None
    for i in range(1,3):
        Log("Attempting to download XML: Try #%d" % i)
        #Header for XML Request
        headers = { 
            'Host' : 'gamecenter.nhl.com',
            'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)',
            'Accept' : '*/*',
            'Referer' : 'http://gamecenter.nhl.com/nhlgc/console.jsp',
            'Accept-Language' : 'de-de',
            'Accept-Encoding' : 'gzip, deflate',
            'Cookie' : Dict['cookies'],
            'Connection' : 'keep-alive',
            'Content-Type' : 'application/x-www-form-urlencoded'
            }
        try:
            request = HTTP.Request(url, headers=headers, values=values)
        except:
            Log("No access to XML.")
            Dict['cookies'] = Login(Prefs['gc_username'], Prefs['gc_password'])
            continue
        if "<code>noaccess</code>" in request.content:
            Log("No access to XML.")
            Dict['cookies'] = Login(Prefs['gc_username'], Prefs['gc_password'])
            continue
        else:
            xml_data = XML.ElementFromString(request.content.strip())
            return xml_data
    if not xml_data:
        Log("Failed to retrieve requested XML.")
        return ObjectContainer(header=L("Error"), message=L("Failed to retrieve necessary data. Please confirm login credentials."))
