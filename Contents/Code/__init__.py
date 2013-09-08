import calendar

# Borrows heavily from the XBMC NHL GameCenter Add-on by Carb0 - http://forum.xbmc.org/showthread.php?tid=118853

Login = SharedCodeService.gamecenter.GCLogin

ARCHIVE_XML	= 'http://gamecenter.nhl.com/nhlgc/servlets/allarchives'
GAMES_XML 	= 'http://gamecenter.nhl.com/nhlgc/servlets/archives'
VAULT_XML 	= 'http://nhl.cdn.neulion.net/u/nhlgc/flex/vault.xml'

ONE_HOUR	= 60 * 60
ONE_DAY 	= ONE_HOUR * 24
ONE_WEEK	= ONE_DAY * 7
ONE_MONTH	= ONE_DAY * 30
####################################################################################################
PREFIX  = "/video/nhl"
NAME    = 'NHL'
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
            header="Error",
            message="You need to provide a valid username and password. Please buy a subscription."
        )

@handler(PREFIX, NAME)
def MainMenu():    
    oc = ObjectContainer()
    #oc.add(DirectoryObject(key=Callback(LiveGames), title="Live Games"))
    oc.add(DirectoryObject(key=Callback(ArchiveGames, condensed=True), title="Condensed Games"))
    oc.add(DirectoryObject(key=Callback(ArchiveGames), title="Archived Games"))
    oc.add(DirectoryObject(key=Callback(ClassicGames), title="Classic Games"))
    oc.add(PrefsObject(title="Preferences"))
    return oc

@route(PREFIX + '/live')
def LiveGames():
    return

@route(PREFIX + '/archive', condensed=bool)
def ArchiveGames(condensed=False):
    oc = ObjectContainer(title2="Archived Games")
    data = GetXML(url=ARCHIVE_XML, values={'date' : 'true', 'isFlex' : 'true'}, cache_length=ONE_DAY)
    seasons = data.xpath('//season')
    seasons.reverse()
    current_season = seasons[0].get('id')
    current_month = seasons[0].xpath('./g')[-1].text.split('/')[0]
    oc.add(DirectoryObject(key=Callback(Games, season=current_season, month=current_month, condensed=condensed), title="Most Recent Games"))
    for entry in seasons:
	season = entry.get('id')
	if int(season) < 2010:
	    ''' links for seasons older than this don't work, so we'll ignore them '''
	    continue
	oc.add(DirectoryObject(key=Callback(Months, season=season), title="%s Season" % season))
    return oc

@route(PREFIX + '/classic')
def ClassicGames():
    oc = ObjectContainer(title2="Classic Games")
    filters = ['Decade', 'Team', 'Key Players', 'Category']
    oc.add(ObjectContainer(key=Callback(UnfilteredClassics), title="All Classic Games"))
    for option in filters:
	oc.add(ObjectContainer(key=Callback(FilteredClassics, option=option), title="Filter by %s" % option))
    return oc

@route(PREFIX + '/unfilteredclassics')
def UnfilteredClassics():
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    return

@route(PREFIX + '/unfilteredclassics')
def FilteredClassics(option):
    data = XML.ElementFromURL(url=VAULT_XML, cacheTime=ONE_WEEK)
    return

@route(PREFIX + '/months', condensed=bool)
def Months(season, condensed=False):
    oc = ObjectContainer(title1="Archived Games", title2="%s Season" % season)
    data = GetXML(url=ARCHIVE_XML, values={'date' : 'true', 'isFlex' : 'true'}, cache_length=ONE_DAY)
    season_dates = data.xpath('//season[@id="'+season+'"]')[0].xpath('./g')
    months = []
    for entry in reversed(season_dates):
	month = entry.text.split('/')[0]
	if not month in months:
	    months.append(month)
	    title = "%s Games" % calendar.month_name[int(month)]
	    oc.add(DirectoryObject(key=Callback(Games, season=season, month=month, condensed=condensed), title=title))
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
	url = 'http://www.nhl.com/ice/gamecenterlive.htm?id=%s0%s%s' % (season, gctype, game_id)
	if condensed:
	    url = url + "#CONDENSED"
	if Prefs['score_summary']:
	    summary = "%s - %s %s" % (awayGoals, homeGoals, result)
	else:
	    summary = None
	oc.add(DirectoryObject(key=Callback(HomeOrAway, url=url, title=title, summary=summary, date=date), title=title, summary=summary))
    return oc

@route(PREFIX + '/homeoraway')
def HomeOrAway(url, title, summary, date):
    oc = ObjectContainer(title2="Choose Feed")
    date = Datetime.ParseDate(date).date()
    oc.add(VideoClipObject(url=url+"#HOME", title="Home Feed", summary="%s\n%s" % (title, summary), originally_available_at=date))
    oc.add(VideoClipObject(url=url+"#AWAY", title="Away Feed", summary="%s\n%s" % (title, summary), originally_available_at=date))
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
        request = HTTP.Request(url, headers=headers, values=values)
        if "<code>noaccess</code>" in request.content:
            Log("No access to XML.")
            Dict['cookies'] = Login(Prefs['gc_username'], Prefs['gc_password'])
        else:
            xml_data = XML.ElementFromString(request.content.strip())
            return xml_data
    if not xml_data:
        Log("Failed to retrieve requested XML.")
        return ObjectContainer(header="Error", message="Failed to retrieve necessary data. Please confirm login credentials.")

#Helpful code from the XBMC NHL-GameCenter Add-on#    
'''
def convertClassicXML(inputfile,outputfile):
    #Load the xml file
    xmlPath = os.path.join(ROOTDIR, inputfile)
    xml = parse(xmlPath)
    games = xml.getElementsByTagName('Row')

    #Create xml document
    doc = Document()
    vault = doc.createElement("vault")
    doc.appendChild(vault)

    #Get games
    for game in games:
        #Get title
        title = game.getElementsByTagName('Data')[7].childNodes[0].nodeValue
        date = re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s(?:\d\d|\d)\S\s\d{4}\S\s', game.getElementsByTagName('Data')[7].childNodes[0].nodeValue)
        c = time.strptime(date[0][:-2],"%B %d, %Y")
        title = time.strftime("%Y-%m-%d",c) + ': ' + game.getElementsByTagName('Data')[7].childNodes[0].nodeValue.replace(date[0], '')
    
        #Get info
        info = game.getElementsByTagName('Data')[8].childNodes[0].nodeValue

        #Get thumbnail
        thumbnail = 'http://nhl.cdn.neulion.net/u/nhl/thumbs/vault/' + game.getElementsByTagName('Data')[11].childNodes[0].nodeValue[:-3] + 'jpg'

        #Get category
        category = game.getElementsByTagName('Data')[9].childNodes[0].nodeValue

        #Get rtmp links
        rtmp_800 = "rtmp://cdncon.fcod.llnwd.net/a277/e4/mp4:s/nhl/svod/flv/vault/" + game.getElementsByTagName('Data')[11].childNodes[0].nodeValue
        rtmp_1600 = "rtmp://cdncon.fcod.llnwd.net/a277/e4/mp4:s/nhl/svod/flv/vault/" + game.getElementsByTagName('Data')[12].childNodes[0].nodeValue

        #Create main element
        xml_game = doc.createElement("game")
        vault.appendChild(xml_game)

        #Create elements
        xml_title = doc.createElement("title")
        xml_info = doc.createElement("info")
        xml_thumbnail = doc.createElement("thumbnail")
        xml_category = doc.createElement("category")
        xml_rtmp_800 = doc.createElement("rtmp_800")
        xml_rtmp_1600 = doc.createElement("rtmp_1600")
        xml_game.appendChild(xml_title)
        xml_game.appendChild(xml_info)
        xml_game.appendChild(xml_thumbnail)
        xml_game.appendChild(xml_category)
        xml_game.appendChild(xml_rtmp_800)
        xml_game.appendChild(xml_rtmp_1600)

        #Insert text
        text = doc.createTextNode(title)
        xml_title.appendChild(text)
        text = doc.createTextNode(info)
        xml_info.appendChild(text)
        text = doc.createTextNode(thumbnail)
        xml_thumbnail.appendChild(text)
        text = doc.createTextNode(category)
        xml_category.appendChild(text)
        text = doc.createTextNode(rtmp_800)
        xml_rtmp_800.appendChild(text)
        text = doc.createTextNode(rtmp_1600)
        xml_rtmp_1600.appendChild(text)


    #Save the XML
    saveFile(outputfile,doc.toxml('utf-8'))

def VIDEOLINKS(url,name):
    #Load the xml file
    month = url[-7:-5]
    year = url[-12:-8]
    gameid = url[-4:]
    condensed = 'false'
    if url[1:9] == 'condensed':
        condensed = 'true'

    if condensed == 'true' or int(year) >= 2012:
        xmlPath = os.path.join(ROOTDIR, "xml/condensed.xml")
    else:
        xmlPath = os.path.join(ROOTDIR, "xml/games.xml")

    xml = parse(xmlPath)
    games = xml.getElementsByTagName("game")

    #Video URLs
    home_url = ''
    away_url = ''

    #Videotitle
    videotitle = ''

    #Icon path
    iconPath = ''

    #Show home and away feed for chosen game
    for game in games:
        gid = game.getElementsByTagName("gid")[0].childNodes[0].nodeValue
        date = game.getElementsByTagName("date")[0].childNodes[0].nodeValue
        homeTeam = game.getElementsByTagName("homeTeam")[0].childNodes[0].nodeValue
        awayTeam = game.getElementsByTagName("awayTeam")[0].childNodes[0].nodeValue
        
        if int(gid) == int(gameid):
            playPathPart1 = game.getElementsByTagName("program")[0].getElementsByTagName("publishPoint")[0].childNodes[0].nodeValue[37:][:-49]
            playPathPart2 = game.getElementsByTagName("program")[0].getElementsByTagName("publishPoint")[0].childNodes[0].nodeValue[-45:]

            #Versus string
            versus = 31400
            if ALTERNATIVEVS == 'true':
                versus = 31401

            #Localize the date
            date2 = date[:10]
            date = datetime.fromtimestamp(time.mktime(time.strptime(date2,"%Y-%m-%d"))).strftime(xbmc.getRegion('dateshort'))

            #Get teamnames
            teams = getTeams()
        
            #Set videotitle
            videotitle = date + ': ' + teams[awayTeam][TEAMNAME] + " " + local_string(versus) + " " + teams[homeTeam][TEAMNAME]

            #Set icon path
            if USETHUMBNAILS == 'true':
                iconPath = os.path.join(ROOTDIR, "resources/images/" + THUMBFORMATOSD + "_" + BACKGROUNDOSD + "/"+ awayTeam + "vs" + homeTeam + ".png")

            if USERTMP == 'true':
                #Use RTMP streams
                if QUALITYRTMP == 1:
                    quality = "hd"
                else:
                    quality = "sd"
                
                rtmp_url = "rtmp://cdncon.fcod.llnwd.net app=a277/e4 playpath=" + playPathPart1 + "_" + quality + playPathPart2 + " swfUrl=http://nhl.cdn.neulion.net/u/nhlgc/console.swf swfVfy=false live=false"
                home_url = rtmp_url
                
                rtmp_url = rtmp_url.replace('_h_', '_a_')
                away_url = rtmp_url
            else:
                #Use HTTP streams
                if QUALITY == 4:
                    quality = ""
                elif QUALITY == 3:
                    quality = "_4500"
                    if int(year) >= 2012:
                        quality = "_4500"
                    else:
                        quality = "_3000"
                elif QUALITY == 2:
                    quality = "_3000"
                elif QUALITY == 1:
                    quality = "_1600"
                else:
                    quality = "_800"

                #Quality Dialog
                if SHOWDIALOGQUALITY == 'true':
                    availableFeeds = [local_string(31360),local_string(31361),local_string(31362),local_string(31363),local_string(31364)]
                    dialog = xbmcgui.Dialog()
                    ret = dialog.select(local_string(31310), availableFeeds)
                    if ret == 0:
                        quality = ""
                    elif ret == 1:
                        quality = "_4500"
                        if int(year) >= 2012:
                            quality = "_4500"
                        else:
                            quality = "_3000"
                    elif ret == 2:
                            quality = "_3000"
                    elif ret == 3:
                        quality = "_1600"
                    elif ret == 4:
                        quality = "_800"
                        
                http_url = "http://nhl.cdn.neulion.net/" + playPathPart1[4:] + "/v1/playlist" + quality + ".m3u8"
                http_url = http_url.replace('/pc/', '/ced/')

                #Fix for 2012-2013 season
                if int(year) >= 2012:
                    http_url = http_url.replace('http://nhl.cdn.neulion.net/', 'http://nlds150.cdnak.neulion.com/')
                    http_url = http_url.replace('s/nhlmobile/vod/nhl/', 'nlds_vod/nhl/vod/')
                    http_url = http_url.replace('/v1/playlist', '')
                    http_url = http_url.replace('.m3u8', '_ced.mp4.m3u8')

                    #Fix for early games in the season
                    http_url = http_url.replace('condensed_ced', 'condensed_1_ced')
                    http_url = http_url.replace('condensed_4500', 'condensed_1_4500')
                    http_url = http_url.replace('condensed_3000', 'condensed_1_3000')
                    http_url = http_url.replace('condensed_1600', 'condensed_1_1600')
                    http_url = http_url.replace('condensed_800', 'condensed_1_800')

                    #Fix for some streams
                    http_url = http_url.replace('s/as3/', '')
                    
                    if url[:8] == '/archive':
                        http_url = http_url.replace('condensed', 'whole')


                home_url = http_url
                
                http_url = http_url.replace('_h_', '_a_')
                away_url = http_url

                print http_url

            
def LIVE(url,name):
    #Download live.xml
    url2 = 'http://cedrss.neulion.com/nhlgc/archives/?live=true&user=' + USERNAME + '&pass=' + PASSWORD
    response = urllib2.urlopen(url2)
    downloadedXML = response.read()

    #Save the xml file
    saveFile("xml/live.xml",downloadedXML)

    #Load the xml file
    xmlPath = os.path.join(ROOTDIR, "xml/live.xml")
    xml = parse(xmlPath)
    games = xml.getElementsByTagName('item')

    #Get teamnames
    teams = getTeams()
        
    #Invert teams dictionary
    teams2 = {}
    for team in teams.keys():
        teams2[teams[team][4]] = team
        
    for game in games:
        #Setup variables
        awayTeam = ''
        homeTeam = ''
        date = ''
        live = ''
        live2 = ''
        
        for element in game.getElementsByTagName('boxee:property'):
            if element.attributes["name"].value == 'custom:awayName':
               awayTeam = teams2[element.childNodes[0].nodeValue]

            if element.attributes["name"].value == 'custom:homeName':
               homeTeam = teams2[element.childNodes[0].nodeValue]

            if element.attributes["name"].value == 'custom:gameState' and element.childNodes:
               live = element.childNodes[0].nodeValue

            if element.attributes["name"].value == 'custom:result' and element.childNodes:
               live2 = element.childNodes[0].nodeValue
               
            if element.attributes["name"].value == 'custom:startTime':
               date = element.childNodes[0].nodeValue


        #Game title
        title = game.getElementsByTagName('description')[0].childNodes[0].nodeValue

        #Get start time
        gameStarted = re.findall(r'\d{2}\S\d{2}\S\d{4}\s\d{2}\S\d{2}', title)
        c = time.strptime(date,"%m/%d/%Y %H:%M:%S")

        if not gameStarted:
            #Displayed titlestring
            if live == 'FINAL' or live2 == 'FINAL':
                title = live + ': ' + teams[awayTeam][TEAMNAME] + " " + local_string(31400) + " " + teams[homeTeam][TEAMNAME]
            else:
                title = live + ' - ' + live2 + ': ' + teams[awayTeam][TEAMNAME] + " " + local_string(31400) + " " + teams[homeTeam][TEAMNAME]
        else:
            #Convert the time to the local timezone
            date = datetime.fromtimestamp(time.mktime(c))
            date = date.replace(tzinfo=tz.gettz('America/New_York'))
            datelocal = date.astimezone(tz.tzlocal()).strftime(xbmc.getRegion('dateshort')+' '+xbmc.getRegion('time').replace('%H%H','%H').replace(':%S',''))

            #Versus string
            versus = 31400
            if ALTERNATIVEVS == 'true':
                versus = 31401
            
            #Displayed titlestring
            title = datelocal + ': ' + teams[awayTeam][TEAMNAME] + " " + local_string(versus) + " " + teams[homeTeam][TEAMNAME]
            
            
        #Icon path
        iconPath =''
        if USETHUMBNAILS == 'true':
            iconPath = os.path.join(ROOTDIR, "resources/images/" + THUMBFORMAT + "_" + BACKGROUND + "/"+ awayTeam + "vs" + homeTeam + ".png")
            
        #Add game
        if SHOWHADIALOGLIVE == 'true':
            addDir2(title,url + game.getElementsByTagName('description')[0].childNodes[0].nodeValue,9,iconPath)
        else:
            addDir(title,url + game.getElementsByTagName('description')[0].childNodes[0].nodeValue,9,iconPath)
        

def LIVELINKS(url,name):    
    #Load the xml file
    xmlPath = os.path.join(ROOTDIR, "xml/live.xml")
    xml = parse(xmlPath)
    games = xml.getElementsByTagName('item')

    #Video URLs
    home_url = ''
    away_url = ''

    #Videotitle
    videotitle = name

    #Icon path
    iconPath = ''

    #Get teamnames
    teams = getTeams()
        
    #Invert teams dictionary
    teams2 = {}
    for team in teams.keys():
        teams2[teams[team][4]] = team
        
    for game in games:
        if game.getElementsByTagName('description')[0].childNodes[0].nodeValue == url[5:]:
            #Quality settings
            if int(settings.getSetting( id="quality")) == 4:
                quality = "_ced."
            elif int(settings.getSetting( id="quality")) == 3:
                quality = "_ced."
            elif int(settings.getSetting( id="quality")) == 2:
                quality = "_3000_ced."
            elif int(settings.getSetting( id="quality")) == 1:
                quality = "_1600_ced."
            else:
                quality = "_800_ced."

            #Get teamlogos
            awayTeam = ''
            homeTeam = ''
            
            for element in game.getElementsByTagName('boxee:property'):
                if element.attributes["name"].value == 'custom:awayName':
                   awayTeam = teams2[element.childNodes[0].nodeValue]

                if element.attributes["name"].value == 'custom:homeName':
                   homeTeam = teams2[element.childNodes[0].nodeValue]
                   
            #Set icon path
            if USETHUMBNAILS == 'true':
                iconPath = os.path.join(ROOTDIR, "resources/images/" + THUMBFORMATOSD + "_" + BACKGROUNDOSD + "/"+ awayTeam + "vs" + homeTeam + ".png")
            
            #Home/away feeds
            for element in game.getElementsByTagName('boxee:property'):
                if "|gcl" in open(os.path.join(ROOTDIR, "cookies")).read():
                    #Home feed
                    if element.attributes["name"].value == 'custom:home-video-stream':
                        if LIVEPLAYBACK == 1:#Alternative
                            #Download
                            url2 = element.childNodes[0].nodeValue.replace('_ced.', quality)
                            response = urllib2.urlopen(url2)
                            downloadedXML = response.read()

                            #Save the xml file
                            saveFile("home.m3u8",downloadedXML)
    
                            home_url = os.path.join(ROOTDIR, "home.m3u8")
                        else:#Standard
                            http_url = element.childNodes[0].nodeValue
                            if SHOWDIALOGQUALITY != 'true':
                                http_url = element.childNodes[0].nodeValue.replace('_ced.', quality)
                            home_url = http_url
                    #Away feed
                    if element.attributes["name"].value == 'custom:away-video-stream':
                        if LIVEPLAYBACK == 1:#Alternative
                            #Download
                            url2 = element.childNodes[0].nodeValue.replace('_ced.', quality)
                            response = urllib2.urlopen(url2)
                            downloadedXML = response.read()

                            #Save the xml file
                            saveFile("away.m3u8",downloadedXML)
    
                            away_url = os.path.join(ROOTDIR, "away.m3u8")
                        else:#Standard
                            http_url = element.childNodes[0].nodeValue
                            if SHOWDIALOGQUALITY != 'true':
                                http_url = element.childNodes[0].nodeValue.replace('_ced.', quality)
                            away_url = http_url
                        

    #'Choose a feed' dialog box
    if (home_url != '') or (away_url != ''):
        
        if SHOWDIALOGQUALITY == 'true':
            availableFeeds = [local_string(31360),local_string(31361),local_string(31362),local_string(31363),local_string(31364)]
            dialog = xbmcgui.Dialog()
            ret = dialog.select(local_string(31310), availableFeeds)
            if ret == 0:
                home_url = home_url.replace('_ced.', '_ced.')
                away_url = away_url.replace('_ced.', '_ced.')
            elif ret == 1:
                home_url = home_url.replace('_ced.', '_ced.')
                away_url = away_url.replace('_ced.', '_ced.')
            elif ret == 2:
                home_url = home_url.replace('_ced.', '_3000_ced.')
                away_url = away_url.replace('_ced.', '_3000_ced.')
            elif ret == 3:
                home_url = home_url.replace('_ced.', '_1600_ced.')
                away_url = away_url.replace('_ced.', '_1600_ced.')
            elif ret == 4:
                home_url = home_url.replace('_ced.', '_800_ced.')
                away_url = away_url.replace('_ced.', '_800_ced.')
                

        if SHOWHADIALOGLIVE == 'true':
            dialog = xbmcgui.Dialog()
            ret = dialog.yesno(local_string(31300), local_string(31310),'','',local_string(31320),local_string(31330))
            if ret == 0:
                print "HOME"
                liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconPath)
                liz.setInfo( type="Video", infoLabels={ "Title": videotitle } )
                xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(home_url,liz)                
            else:
                print "AWAY"
                liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconPath)
                liz.setInfo( type="Video", infoLabels={ "Title": videotitle } )
                xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(away_url,liz)
        else:
            addLink('Home',home_url,name,iconPath)
            addLink('Away',away_url,name,iconPath)
    else:
        dialog = xbmcgui.Dialog()
        if name[:5] == 'FINAL':
            ret = dialog.ok(local_string(31300), local_string(31370))
        else:
            ret = dialog.ok(local_string(31300), local_string(31380))


def CLASSIC(url,name):
    #Download and convert the xml file
    try:
       open(os.path.join(ROOTDIR, "xml/vault.xml"))
    except IOError:
       downloadXMLDataClassic('http://nhl.cdn.neulion.net/u/nhlgc/flex/vault.xml',"xml/vault.xml")
       convertClassicXML("xml/vault.xml","xml/vault2.xml")

    #Download again if the file is too old
    st = os.stat(os.path.join(ROOTDIR, "xml/vault.xml"))    
    fileage = st.st_mtime
    now = time.time()
    delta = now - fileage
    
    if delta >= 604800: #one week
        downloadXMLDataClassic('http://nhl.cdn.neulion.net/u/nhlgc/flex/vault.xml',"xml/vault.xml")
        convertClassicXML("xml/vault.xml","xml/vault2.xml")
    
    #Load the xml file
    xmlPath = os.path.join(ROOTDIR, "xml/vault2.xml")
    xml = parse(xmlPath)
    games = xml.getElementsByTagName('game')

    #Get categories
    output = []
    for game in games:
        if game.getElementsByTagName('category')[0].childNodes[0].nodeValue not in output:
            output.append(game.getElementsByTagName('category')[0].childNodes[0].nodeValue)
            addDir(game.getElementsByTagName('category')[0].childNodes[0].nodeValue,url + game.getElementsByTagName('category')[0].childNodes[0].nodeValue,11,ICON)


def CLASSIC2(url,name):
    #Load the xml file
    xmlPath = os.path.join(ROOTDIR, "xml/vault2.xml")
    xml = parse(xmlPath)
    games = xml.getElementsByTagName('game')

    #Get games
    for game in games:
        if game.getElementsByTagName('category')[0].childNodes[0].nodeValue == name:

            #Video title
            title = game.getElementsByTagName('title')[0].childNodes[0].nodeValue

            #Icon path
            iconPath =''
            if USETHUMBNAILS == 'true':
                iconPath = game.getElementsByTagName('thumbnail')[0].childNodes[0].nodeValue
                
            #Add game
            addDir2(title, url + game.getElementsByTagName('title')[0].childNodes[0].nodeValue,12,iconPath)


def CLASSICVIDEOLINKS(url,name):
    #Load the xml file
    xmlPath = os.path.join(ROOTDIR, "xml/vault2.xml")
    xml = parse(xmlPath)
    games = xml.getElementsByTagName('game')

    #Videotitle
    videotitle = name
    
    #Icon Path
    iconPath = ''
    
    #Get link
    for game in games:
        if game.getElementsByTagName('title')[0].childNodes[0].nodeValue == name:

            #Download thumbnail
            if USETHUMBNAILS == 'true':
                iconPath = game.getElementsByTagName('thumbnail')[0].childNodes[0].nodeValue
            
            #Check quality settings
            if QUALITYRTMP == 0:
                #800kbit/s
                path = game.getElementsByTagName('rtmp_800')[0].childNodes[0].nodeValue
                values = {'isFlex' : 'true', 'type' : 'fvod', 'path' : path}
                downloadXMLData('http://gamecenter.nhl.com/nhlgc/servlets/encryptvideopath ',values,"xml/classicvideopath.xml",'true')
            else:
                #1600kbit/s
                path = game.getElementsByTagName('rtmp_1600')[0].childNodes[0].nodeValue
                values = {'isFlex' : 'true', 'type' : 'fvod', 'path' : path}
                downloadXMLData('http://gamecenter.nhl.com/nhlgc/servlets/encryptvideopath ',values,"xml/classicvideopath.xml",'true')
                
    #Get rtmp url
    xmlPath = os.path.join(ROOTDIR, "xml/classicvideopath.xml")
    xml = parse(xmlPath)
    playpath = xml.getElementsByTagName('path')[0].childNodes[0].nodeValue.replace('rtmp://cdncon.fcod.llnwd.net/a277/e4/','')
    rtmp_url = 'rtmp://cdncon.fcod.llnwd.net app=a277/e4 playpath=' + playpath                   

    #Play
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconPath)
    liz.setInfo( type="Video", infoLabels={ "Title": videotitle } )
    xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(rtmp_url,liz)

'''

#Teams
'''
CHI, Chicago, Blackhawks, Chicago Blackhawks, CHI, Blackhawks
CMB, Columbus, Blue Jackets, Columbus Blue Jackets,CMB, BlueJackets
DET, Detroit, Red Wings, Detroit Red Wings, DET, RedWings
NSH, Nashville, Predators, Nashville Predators, NSH, Predators
STL, St. Louis, Blues, St. Louis Blues, STL, Blues
NJD, New Jersey, Devils, New Jersey Devils, NJD, Devils
NYI, NY Islanders, Islanders, New York Islanders, NYI, Islanders
NYR, NY Rangers, Rangers, New York Rangers, NYR, Rangers
PHI, Philadelphia, Flyers, Philadelphia Flyers, PHI, Flyers
PIT, Pittsburgh, Penguins, Pittsburgh Penguins, PIT, Penguins
CGY, Calgary, Flames, Calgary Flames, CGY, Flames
COL, Colorado, Avalanche, Colorado Avalanche, COL, Avalanche
EDM, Edmonton, Oilers, Edmonton Oilers, EDM, Oilers
MIN, Minnesota, Wild, Minnesota Wild, MIN, Wild
VAN, Vancouver, Canucks, Vancouver Canucks, VAN, Canucks
BOS, Boston, Bruins, Boston Bruins, BOS, Bruins
BUF, Buffalo, Sabres, Buffalo Sabres, BUF, Sabres
MON, Montreal, Canadiens, Montreal Canadiens, MON, Canadiens
OTT, Ottawa, Senators, Ottawa Senators, OTT, Senators
TOR, Toronto, Maple Leafs, Toronto Maple Leafs, TOR, MapleLeafs
ANA, Anaheim, Ducks, Anaheim Ducks, ANA, Ducks
DAL, Dallas, Stars, Dallas Stars,DAL, Stars
LOS, Los Angeles, Kings, Los Angeles Kings, LOS, Kings
PHX, Phoenix, Coyotes, Phoenix Coyotes, PHX, Coyotes
SAN, San Jose, Sharks, San Jose Sharks, SAN, Sharks
CAR, Carolina, Hurricanes, Carolina Hurricanes, CAR, Hurricanes
FLA, Florida, Panthers, Florida Panthers, FLA, Panthers
TAM, Tampa Bay, Lightning, Tampa Bay Lightning, TAM, Lightning
WSH, Washington, Capitals, Washington Capitals, WSH, Capitals
WPG, Winnipeg, Jets, Winnipeg Jets, WPG, Jets
'''
