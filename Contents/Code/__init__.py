# Borrows heavily from the XBMC NHL GameCenter Add-on by Carb0 - http://forum.xbmc.org/showthread.php?tid=118853

Login = SharedCodeService.gamecenter.GCLogin

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

    HTTP.Headers['User-agent'] = 'Mozilla/5.0 (iPad; U; CPU OS 3_2_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B500 Safari/531.21.10'

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
    
    #dir.Append(Function(DirectoryItem(NHLMenu, title="NHL.com", thumb=R(NHL), art=R(ART))))
    #dir.Append(Function(DirectoryItem(GCMainMenu, title="NHL Gamecenter Live", thumb=R(NHL), art=R(ART))))
    oc.add(PrefsObject(title="Preferences"))
        
    return oc

@route(PREFIX + '/')
def GetXML(url, values):
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
        request = HTTP.Request(url, headers=header, values=values)
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
import xbmcplugin, xbmcgui, xbmcaddon
import re, os, time
import urllib, urllib2, httplib2
import thumbnailgenerator
from xml.dom.minidom import Document, parse, parseString
from datetime import datetime, date, timedelta, tzinfo
from dateutil import tz

# 
############################################################################

#Set root path
ROOTDIR = xbmcaddon.Addon(id='plugin.video.nhl-gamecenter').getAddonInfo('path')

#Settings
settings = xbmcaddon.Addon(id='plugin.video.nhl-gamecenter')

#Main settings
USERNAME = settings.getSetting(id="username")
PASSWORD = settings.getSetting(id="password")
QUALITY = int(settings.getSetting(id="quality"))
QUALITYRTMP = int(settings.getSetting(id="qualityrtmp"))
USERTMP = settings.getSetting(id="usertmp")
LIVEPLAYBACK = 0

SHOWDIALOGQUALITY = 'true'
if QUALITY != 5:
    SHOWDIALOGQUALITY = 'false'

#Visual settings
TEAMNAME = int(settings.getSetting(id="team_names"))
HIDELIVEGAMES = settings.getSetting(id="hide_live_games")
USETHUMBNAILS = settings.getSetting(id="use_thumbnails")
USEADDONICON = settings.getSetting(id="use_addon_icon")

if (USEADDONICON == 'true') and (USETHUMBNAILS == 'true'):
    ICON = os.path.join(ROOTDIR, "icon.png")
else:
    ICON = ''
    
thumbnail = ["square","cover","169"]
background = ["black","ice","transparent"]

THUMBFORMAT = thumbnail[int(settings.getSetting(id="thumb_format"))]
THUMBFORMATOSD = thumbnail[int(settings.getSetting(id="thumb_format_osd"))]
BACKGROUND = background[int(settings.getSetting(id="background"))]
BACKGROUNDOSD = background[int(settings.getSetting(id="background_osd"))]
GENERATETHUMBNAILS = settings.getSetting(id="generate_thumbnails")
DELETETHUMBNAILS = settings.getSetting(id="delete_thumbnails")
SHOWHADIALOG = settings.getSetting(id="showhadialog")
SHOWHADIALOGLIVE = settings.getSetting(id="showhadialoglive")
ALTERNATIVEVS = settings.getSetting(id="alternativevs")


#Localisation
local_string = xbmcaddon.Addon(id='plugin.video.nhl-gamecenter').getLocalizedString

#Content type
#xbmcplugin.setContent(int(sys.argv[1]), 'episodes')


#TEAM NAMES
############################################################################

def getTeams():
    allTeams = {}
    infile = open(os.path.join(ROOTDIR, 'teams'),'r')
    lines = infile.readlines()

    for i in lines:

        short = ''
        teamnames = []
        
        for idx,item in enumerate(i.split(',')):
            if idx == 0:
                short = item.strip()
            else:
                teamnames.append(item.strip())
                
        allTeams.setdefault(short, teamnames)

    return allTeams


#LOGIN & XML DOWNLOAD
############################################################################   

def saveFile(filename,content):
    #Save File
    fileObj = open(os.path.join(ROOTDIR, filename),"w")
    fileObj.write(content)
    fileObj.close()
    print filename + ' saved'


def login():
    #Login
    print 'Logging in...'
    
    http = httplib2.Http()
    http.disable_ssl_certificate_validation=True

    url = 'https://gamecenter.nhl.com/nhlgc/secure/login'
    body = {'username': USERNAME, 'password': PASSWORD}
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    response, content = http.request(url, 'POST', headers=headers, body=urllib.urlencode(body))

    #Save Cookies
    saveFile("cookies",response['set-cookie'])


def downloadXMLData(url,values,filename,classic):

    http = httplib2.Http()
    http.disable_ssl_certificate_validation=True
    
    for i in range(1, 3):
        print "Download: " + str(i) + ". try"
        
	#Load Cookies
        try:
            cookies = open(os.path.join(ROOTDIR, "cookies")).readline()
        except IOError:
            login()
            cookies = open(os.path.join(ROOTDIR, "cookies")).readline()
            
        #Header for XML Request
        headers = { 'Host' : 'gamecenter.nhl.com',
                    'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)',
                    'Accept' : '*/*',
                    'Referer' : 'http://gamecenter.nhl.com/nhlgc/console.jsp',
                    'Accept-Language' : 'de-de',
                    'Accept-Encoding' : 'gzip, deflate',
                    'Cookie' : cookies,
                    'Connection' : 'keep-alive',
                    'Content-Type' : 'application/x-www-form-urlencoded'}
        
        #Download the XML
        if classic == 'true':
            valuesencoded = urllib.urlencode(values).replace('.','%2E').replace('_','%5F').replace('-','%2D')
            response, content = http.request(url, 'POST', headers=headers, body=valuesencoded)
        else:
            response, content = http.request(url, 'POST', headers=headers, body=urllib.urlencode(values))
            
        downloadedXML = content.strip()
        
        #Try to login again if XML not accessible
        if "<code>noaccess</code>" in downloadedXML:
            print "No access to XML file"
            login()
            continue
        else:
            print "Download successful"

            #Save the XML
            saveFile(filename,downloadedXML)
            break
    else:
        print "Login failed. Check your login credentials."

        #Save the XML
        saveFile(filename,downloadedXML)

       
def downloadXMLDataClassic(url,filename):
    response = urllib2.urlopen(url)
    downloadedXML = response.read().strip()
    print "Download successful"

    #Save the XML
    saveFile(filename,downloadedXML)


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



#XBMC INTERFACE  
############################################################################

def CATEGORIES():
    #Show progressbar
    progress = None
    i = 0
    steps = 0.0
    if (DELETETHUMBNAILS == 'true') or (GENERATETHUMBNAILS == 'true'):
        progress = xbmcgui.DialogProgress()
        
        if DELETETHUMBNAILS == 'true':
            steps = steps + 1
        if GENERATETHUMBNAILS == 'true':
            steps = steps + 1
        if (THUMBFORMAT != THUMBFORMATOSD) or (BACKGROUND != BACKGROUNDOSD):
            steps = steps + 1
        
        progress.create(local_string(31300), '')
        percent = int( ( i / steps ) * 100)
        message = local_string(31350)
        progress.update( percent, "", message, "" )
        i = i + 1
        print percent, steps
        
    #Delete thumbnails
    if DELETETHUMBNAILS == 'true':
        thumbnailgenerator.deleteThumbnails(ROOTDIR)

        #Reset setting
        settings.setSetting(id='delete_thumbnails', value='false')

        #Update progressbar
        percent = int( ( i / steps ) * 100)
        message = local_string(31350)
        progress.update( percent, "", message, "" )
        i = i + 1
        print percent, steps

    #Create thumbnails
    if GENERATETHUMBNAILS == 'true':
        thumbnailgenerator.createThumbnails(ROOTDIR,THUMBFORMAT,BACKGROUND)

        #Update progress
        percent = int( ( i / steps ) * 100)
        message = local_string(31350)
        progress.update( percent, "", message, "" )
        i = i + 1
        print percent, steps
        
        if (THUMBFORMAT != THUMBFORMATOSD) or (BACKGROUND != BACKGROUNDOSD):
            thumbnailgenerator.createThumbnails(ROOTDIR,THUMBFORMATOSD,BACKGROUNDOSD)

            #Update progress
            percent = int( ( i / steps ) * 100)
            message = local_string(31350)
            progress.update( percent, "", message, "" )
            i = i + 1
            print percent, steps
        
        #Reset setting
        settings.setSetting(id='generate_thumbnails', value='false')

    #Close progressbar
    if (DELETETHUMBNAILS == 'true') or (GENERATETHUMBNAILS == 'true'):
        progress.close()
    

    #Login if cookies aren't set
    try:
       open(os.path.join(ROOTDIR, "cookies"))
    except IOError:
       login()

    
    if (USERNAME in open(os.path.join(ROOTDIR, "cookies")).read()) and USERNAME != '':
        #Show categories
        if HIDELIVEGAMES == 'false':
            addDir(local_string(31100),'/live',8,ICON)
        addDir(local_string(31110),'/condensed',1,ICON)
        addDir(local_string(31120),'/archive',1,ICON)
        addDir(local_string(31130),'/classic',10,ICON)
    else:
        os.remove(os.path.join(ROOTDIR, "cookies"))
        print "cookies removed"
        
        dialog = xbmcgui.Dialog()
        dialog.ok('Login failed', 'Check your login credentials')
        xbmcplugin.endOfDirectory(handle = int(sys.argv[1]),succeeded=False)
        return None


def YEAR(url):
    #Download the xml file
    downloadXMLData('http://gamecenter.nhl.com/nhlgc/servlets/allarchives',{'date' : 'true', 'isFlex' : 'true'},"xml/archive.xml",'false')

    #Get available seasons
    xmlPath = os.path.join(ROOTDIR, "xml/archive.xml")
    xml = parse(xmlPath)
    seasons = xml.getElementsByTagName("season")

    for season in reversed(seasons):
        print season.attributes["id"].value
        if (season.attributes["id"].value == "2007"):#Links don't work
            break
        elif (season.attributes["id"].value == "2008"):#Links don't work
            break
        elif (season.attributes["id"].value == "2009"):#Links don't work
            break
        else:
            addDir( season.attributes["id"].value + ' - ' + str(int(season.attributes["id"].value) + 1),url+'/'+season.attributes["id"].value,2,ICON)


def MONTH(url,name):
    #Get available Months
    xmlPath = os.path.join(ROOTDIR, "xml/archive.xml")
    xml = parse(xmlPath)
    seasons = xml.getElementsByTagName("season")

    firstmonth = ''
    lastmonth = ''
    
    for season in seasons:
        if season.attributes["id"].value == name[:-7]:
            dates = season.getElementsByTagName("g")
            if len(dates[0].childNodes[0].nodeValue)>10: #Fix for alternative date format
                firstmonth = dates[0].childNodes[0].nodeValue[5:7]
                lastmonth = dates[len(dates)-1].childNodes[0].nodeValue[5:7]
            else:
                firstmonth = dates[0].childNodes[0].nodeValue[:2]
                lastmonth = dates[len(dates)-1].childNodes[0].nodeValue[:2]

            
    #Add directories
    i = int(lastmonth)

    while i >= 1:
        if i==1:
            addDir(local_string(31201),url+'/01',3,ICON)
        elif i==2:
            addDir(local_string(31202),url+'/02',3,ICON)
        elif i==3:
            addDir(local_string(31203),url+'/03',3,ICON)
        elif i==4:
            addDir(local_string(31204),url+'/04',3,ICON)
        elif i==5:
            addDir(local_string(31205),url+'/05',3,ICON)
        elif i==6:
            addDir(local_string(31206),url+'/06',3,ICON)
        elif i==7:
            addDir(local_string(31207),url+'/07',3,ICON)
        elif i==8:
            addDir(local_string(31208),url+'/08',3,ICON)
        elif i==9:
            addDir(local_string(31209),url+'/09',3,ICON)
        elif i==10:
            addDir(local_string(31210),url+'/10',3,ICON)
        elif i==11:
            addDir(local_string(31211),url+'/11',3,ICON)
        elif i==12:
            addDir(local_string(31212),url+'/12',3,ICON)
            

        if i == int(firstmonth):
            break
        
        i = i - 1

        if i==0:
            i = 12


def GAMES(url,name):
    #Load the xml file
    month = url[-2:]
    year = url[-7:-3]
    condensed = 'false'
    if url[1:9] == 'condensed':
        condensed = 'true'

    if condensed == 'true' or int(year) >= 2012:
        #Download the xml file
        values = {'season' : year, 'isFlex' : 'true', 'month' : month, 'condensed' : 'true'}
        downloadXMLData('http://gamecenter.nhl.com/nhlgc/servlets/archives',values,"xml/condensed.xml",'false')
        xmlPath = os.path.join(ROOTDIR, "xml/condensed.xml")
    else:
        #Download the xml file
        values = {'season' : year, 'isFlex' : 'true', 'month' : month}
        downloadXMLData('http://gamecenter.nhl.com/nhlgc/servlets/archives',values,"xml/games.xml",'false')
        xmlPath = os.path.join(ROOTDIR, "xml/games.xml")

    #Parse the xml file
    xml = parse(xmlPath)
    games = xml.getElementsByTagName("game")

    #Get available games
    for game in games:
        gid = game.getElementsByTagName("gid")[0].childNodes[0].nodeValue
        date = game.getElementsByTagName("date")[0].childNodes[0].nodeValue
        homeTeam = game.getElementsByTagName("homeTeam")[0].childNodes[0].nodeValue
        awayTeam = game.getElementsByTagName("awayTeam")[0].childNodes[0].nodeValue

        #Versus string
        versus = 31400
        if ALTERNATIVEVS == 'true':
            versus = 31401

        #Localize the date
        date2 = date[:10]
        date = datetime.fromtimestamp(time.mktime(time.strptime(date2,"%Y-%m-%d"))).strftime(xbmc.getRegion('dateshort'))

        #Get teamnames
        teams = getTeams()
        
        #Game title
        name = date + ': ' + teams[awayTeam][TEAMNAME] + " " + local_string(versus) + " " + teams[homeTeam][TEAMNAME]

        #Icon path
        iconPath =''
        if USETHUMBNAILS == 'true':
            iconPath = os.path.join(ROOTDIR, "resources/images/" + THUMBFORMAT + "_" + BACKGROUND + "/"+ awayTeam + "vs" + homeTeam + ".png")

        #Add directories
        if SHOWHADIALOG == 'true':
            addDir2(name,url+"/"+gid,4,iconPath)
        else:
            addDir(name,url+"/"+gid,4,iconPath)
        

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

            
    if SHOWHADIALOG == 'true':
        #'Choose a feed' dialog box
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
        #'Choose a feed' directory
        addLink("Home",home_url,videotitle,iconPath)
        addLink("Away",away_url,videotitle,iconPath)


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

    
def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                            
    return param


def addLink(name,url,title,iconimage):
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": title } )
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)
    return ok

def addDir(name,url,mode,iconimage):
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    return ok

def addDir2(name,url,mode,iconimage):
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
    return ok

             
params=get_params()
url=None
name=None
mode=None

try:
    url=urllib.unquote_plus(params["url"])
except:
    pass
try:
    name=urllib.unquote_plus(params["name"])
except:
    pass
try:
    mode=int(params["mode"])
except:
    pass

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)

if mode==None or url==None or len(url)<1:
    print ""
    CATEGORIES()
   
elif mode==1:
    print ""+url
    YEAR(url)

elif mode==2:
    print ""+url
    MONTH(url,name)        

elif mode==3:
    print ""+url
    GAMES(url,name)

elif mode==4:
    print ""+url
    VIDEOLINKS(url,name)

elif mode==8:
    print ""+url
    LIVE(url,name)

elif mode==9:
    print ""+url
    LIVELINKS(url,name)
    
elif mode==10:
    print ""+url
    CLASSIC(url,name)

elif mode==11:
    print ""+url
    CLASSIC2(url,name)

elif mode==12:
    print ""+url
    CLASSICVIDEOLINKS(url,name)

xbmcplugin.endOfDirectory(int(sys.argv[1]))

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
