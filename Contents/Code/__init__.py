CW_SEED = 'http://www.cwseed.com'
CW_ROOT = 'http://www.cwtv.com'
ICON     = 'icon-default.png'

RE_JSON = Regex('CWSEED.Site.video_data.videos = (.+)}};', Regex.DOTALL)
####################################################################################################
def Start():

    ObjectContainer.title1 = 'The CW Seed'
    DirectoryObject.thumb = R(ICON)

####################################################################################################
@handler('/video/thecwseed', 'The CW Seed')
def MainMenu():
    
    oc = ObjectContainer()
    html = HTML.ElementFromURL(CW_SEED)
    for item in html.xpath('//div[@id="currentshows"]//a'):
        title = item.xpath('./p/text()')[0]
        show_url = CW_SEED + item.get('href')
        # seed show listings have a blank image for src so we try data-origsrc first
        try: thumb = item.xpath('.//img/@data-origsrc')[0]
        except: thumb = item.xpath('.//img/@src')[0]

        # Whose line must be split into seasons first
        if "Whose Line" in title:
            oc.add(DirectoryObject(
                key = Callback(SeedSeasons, url=show_url, title=title),
                title = title, thumb = Resource.ContentsOfURLWithFallback(thumb)
            ))
        else:
            oc.add(DirectoryObject(
                key = Callback(SeedJSON, url=show_url, title=title),
                title = title, thumb = Resource.ContentsOfURLWithFallback(thumb)
            ))

    return oc
####################################################################################################
# Right now only Whose Line has seasons
@route('/video/thecwseed/seedseasons')
def SeedSeasons(url, title):

    oc = ObjectContainer(title2=title)
    html = HTML.ElementFromURL(CW_SEED)

    for item in html.xpath('//div[@id="whoseline-seasons-menu"]/ul/li/a'):
        url = CW_ROOT + item.xpath('./@href')[0]
        title = item.xpath('.//text()')[0]
        season = title.split()[1].strip()
        oc.add(DirectoryObject(
            key = Callback(SeedJSON, url=url, title=title, season=season),
            title = title
        ))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are currently no seasons for this show')
    else:
        return oc
####################################################################################################
# Pull videos from the json data in the seed formatted video pages
@route('/video/thecwseed/seedjson')
def SeedJSON(url, title, season='0'):

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
        # The guid number is used to pull images from the html
        try: video_thumb = html.xpath('//li[@data-videoguid="%s"]//img/@data-src' %video)[0]
        except: video_thumb = None
        try: duration = int(json[video]['dm'].replace('min', ''))
        except: duration = 0
        show = json[video]['st'].strip()
        episode = json[video]['en'].replace('Ep.', '').strip()
        if not episode:
            episode = '0'
        if len(episode)>3:
            season_num = episode[0] + episode[1]
        else:
            season_num = episode[0]
        # CLEAN OUT VIDEOS IN THE JSON INCLUDING OTHER SHOWS, OTHER SEASONS, OR CLIPS
        # Remove clips
        if duration < 5:
            continue
        duration = duration * 60000
        # Make Terminator title match show field. Other titles with : do not have a leading space
        if " : " in title:
            title = title.replace(' : ', ': ')
        # Whose Line json includes all season and other shows
        if "Season" in title:
            show_title = "Whose Line Is It Anyway?"
            if season!=season_num or show!=show_title:
                continue
        else:
            season = season_num
            if show!=title:
                continue

        oc.add(EpisodeObject(
            show = show,
            season = int(season),
            index = int(episode),
            duration = duration,
            url = video_url,
            title = json[video]['eptitle'],
            summary = json[video]['d'],
            thumb = Resource.ContentsOfURLWithFallback(url=video_thumb)
        ))
        
    # For some reason the json is being sorted out of order so we have to sort it here
    oc.objects.sort(key = lambda obj: obj.index, reverse=True)
        
    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list.")
    else:
        return oc
