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
        cookies = Login(Prefs['gc_username'], Prefs['gc_password'])
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