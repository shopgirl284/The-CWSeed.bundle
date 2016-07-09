CW_SEED = 'http://www.cwseed.com'
CW_ROOT = 'http://www.cwtv.com'
ICON     = 'icon-default.jpg'
RE_JSON = Regex('CWSEED.Site.video_data.videos = (.+)}};', Regex.DOTALL)
####################################################################################################
def Start():

    ObjectContainer.title1 = 'The CW Seed'
    DirectoryObject.thumb = R(ICON)

####################################################################################################
@handler('/video/thecwseed', 'The CW Seed')
def MainMenu():
    
    oc = ObjectContainer()
    
    html = HTML.ElementFromURL(CW_SEED+'/shows/')
    # There is something odd in the shows code that is blocking the ability to access the section that contains images
    # If we use item_list = html.xpath('//li[@class="showitem"]/a') it returns 58 items 
    # for both the mobile and image sections but cannot find titles or images for second group
    # If we use item_list = html.xpath('//div[@id="show-hub"]//li[@class="showitem"]/a') it just fails
    # because it can not find the title or image
    item_list = html.xpath('//li[contains(@class,"showlistgroups")]//li[@class="showitem"]/a')
    #Log('the length of item_list is %s' %len(item_list)) 
    for item in item_list:
        show_url = CW_SEED + item.xpath('./@href')[0]
        title = item.xpath('.//text()')[0]
        #thumb = item.xpath('.//img/@data-src')[0]

        oc.add(DirectoryObject(
            key = Callback(SeedSeasons, url=show_url, title=title),
            title = title
        ))
    # Since this channel contains mostly old shows that will not change, 
    # we offer the option of reversing the episode order for continuous play from Preferences
    oc.add(PrefsObject(title="Preferences", summary="Set Episode Order"))
    if len(oc) < 2:
        return ObjectContainer(header='Empty', message='There are currently no seasons for this show')
    else:
        return oc
####################################################################################################
# Return seasons if listed by seasons or all videos 
@route('/video/thecwseed/seedseasons')
def SeedSeasons(url, title, thumb=''):

    oc = ObjectContainer(title2=title)
    html = HTML.ElementFromURL(url)
    if not thumb:
        thumb = html.xpath('//meta[@id="ogimage"]/@content')[0]
    multi_seasons = html.xpath('//div[contains(@id, "seasons-menu2")]/ul/li/a')

    if multi_seasons:
        for item in multi_seasons:
            url = CW_SEED + item.xpath('./@href')[0]
            seas_title = item.xpath('.//text()')[0]
            season = int(url.split('?season=')[1].strip())
            oc.add(DirectoryObject(
                key = Callback(SeedJSON, url=url, title=seas_title, show_title=title, season=season),
                title = seas_title,
                thumb = Resource.ContentsOfURLWithFallback(url=thumb)
            ))
    else:
        oc.add(DirectoryObject(key = Callback(SeedJSON, url=url, title="All Videos", show_title=title, season=0), title = "All Videos"))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are currently no seasons for this show')
    else:
        return oc
####################################################################################################
# Pull videos from the json data in the seed formatted video pages
@route('/video/thecwseed/seedjson', season=int)
def SeedJSON(url, title, season, show_title):

    oc = ObjectContainer(title2=title)
    content = HTTP.Request(url).content
    html = HTML.ElementFromString(content)
    try:
        json_data = RE_JSON.search(content).group(1) + "}}"
        json = JSON.ObjectFromString(json_data)
    except:
        return ObjectContainer(header="Empty", message="No json data to pull videos")

    for video in json:
        video_url = CW_ROOT + json[video]['url']
        try: duration = int(json[video]['dm'].replace('min', ''))
        except: duration = 0
        # The guid number is used to pull images from the html
        try: video_thumb = html.xpath('//li[@data-videoguid="%s"]//img/@data-src' %video)[0]
        except: video_thumb = None
        episode = json[video]['en'].replace('Ep.', '').strip()
        show = json[video]['st'].strip()
        if episode.isdigit():
            if len(str(season))>1:
                season_num = int(episode[0] + episode[1])
            else:
                season_num = int(episode[0])
            episode=int(episode)
        else:
            season_num = 0
            episode = 0
        # CLEAN OUT VIDEOS FOR OTHER SHOWS, CLIPS, OR OTHER SEASONS
        # Skip videos for other shows
        show_url = url.split('/shows/')[1].split('?')[0]
        if show_url not in video_url:
            continue
        # Skip videos for other seasons
        if season > 0:
            if season!=season_num:
                continue
        # Skip video clips (Some shows are only 3 minutes long)
        if duration < 3:
            continue

        oc.add(EpisodeObject(
            show = show,
            season = season_num,
            index = episode,
            duration = duration * 60000,
            url = video_url,
            title = json[video]['eptitle'],
            summary = json[video]['d'],
            thumb = Resource.ContentsOfURLWithFallback(url=video_thumb)
        ))
        
    # For some reason the json is being sorted out of order so we have to sort it here
    # Prefs do not work currently in latest apps 
    sort_order=Prefs['sort_order'] if Prefs['sort_order'] in (True, False) else False
    oc.objects.sort(key = lambda obj: obj.index, reverse=sort_order)
        
    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list.")
    else:
        return oc
    
