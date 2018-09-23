#! python3
import urllib.request, json
from time import sleep
from datetime import datetime
import re
import json

#########################################################################

# Get list view script (second script). Parse json. Read "rewards">"items">"id" from each element.
# Get data script (first script). Search for pattern _[item_id] and parse following json. Read "name_enus" attribute.
# If we have a match, read "ending" and "id" (quest id) from original json, then also lookup _[quest_id].

def _getWQhtml():
    r = urllib.request.urlopen("https://www.wowhead.com/world-quests/bfa/na")
    r_bytes = r.read()

    wq_html = r_bytes.decode("utf8")
    r.close()

    return wq_html


def _getWQjson(wq_html):

    matcher = '<div class="listview" id="list"></div>'
    wqlist_start = wq_html.index(matcher) + len(matcher)

    wqlist = wq_html[wqlist_start:]

    # Find the next two script tag's contents.
    matcher_in = '<script>'
    matcher_out = '</script>'

    script1_start = wqlist.index(matcher_in) + len(matcher_in)
    script1_end = wqlist.index(matcher_out)

    wqlist_nexttag = wqlist[script1_end+len(matcher_in):]
    script2_start = wqlist_nexttag.index(matcher_in) + len(matcher_in)
    script2_end = wqlist_nexttag.index(matcher_out)

    wqs_data = wqlist[script1_start:script1_end]  # All quest and item data
    wqs_list = wqlist_nexttag[script2_start:script2_end]  # List holding all active WQs

    return (wqs_data, wqs_list)


zone_cache = {"9042": "Stormsong Valley", "8567": "Tiragarde Sound", "8721": "Drustvar", "8499": "Zuldazar", "8500": "Nazmir", "8501": "Vol'dun"}
def _getZoneName(zone_id):
    global zone_cache
    zone_id = str(zone_id)
    if zone_id in zone_cache:
        return zone_cache[zone_id]
    
    # For any unexpected zones
    with open("zone_cache.json", "r") as zf:
        zone_cache = json.load(zf)
        if zone_id in zone_cache:
            return zone_cache[zone_id]

    with urllib.request.urlopen(f"https://www.wowhead.com/zone={zone_id}") as r:
        zone_html = r.read().decode("utf8")
    pat = r"<title>(.+) - Zone - World of Warcraft<\/title>"
    name = re.search(pat, zone_html).group(1)
    zone_cache[zone_id] = name

    with open("zone_cache.json", "w") as zf:
        json.dump(zone_cache, zf)

    return name

def searchWQs(items=[], quests=[]):
    wq_html = _getWQhtml()
    (wqs_data, wqs_list) = _getWQjson(wq_html)

    ## Parse and search WQ list
    list_start = wqs_list.index('{')  # start of json
    list_end = wqs_list.rindex('}')  # end of json
    list_json = wqs_list[list_start:list_end+1]

    list_top = json.loads(list_json)
    list_data = list_top['data']


    # list_data is a list of dictionaries, each dict holding an active WQ
    # list_data.id: The id number for the quest
    # list_data.ending: The ending time for the quest (since epoch?)
    # list_data.rewards: If this is an empty list [], quest gives no rewards
    # list_data.rewards.items: If rewards is non-empty {}, this will hold a list of item dicts
    # list_data.rewards.items.id: If there are item rewards, this will hold their ids.

    output = []
    for quest in list_data:
        quest_id = quest['id']
        quest_endtime = quest['ending']
        rewards = quest['rewards']

        if (type(rewards) is dict):  # if we have any rewards in this quest...
            for item in rewards['items']:
                item_id = item['id']
                item_name = _checkForItem(item_id, wqs_data, items)  # check if this item is in our list
                for item_name, watchlist_item in _checkForItem(item_id, wqs_data, items):
                    # We have a match. Go get the quest name and remaining time on this quest.
                    quest_name = _lookupQuest(quest_id, wqs_data)

                    quest_endtime_formatted = _formatTime(quest_endtime)

                    # Sometimes a quest contains multiple zone IDs
                    _zn = [_getZoneName(x) for x in quest['zones']]
                    zone_names = " in " + " and ".join(_zn) if _zn else "" # Sometimes wowhead doesn't return a zone name
                    highlight_name = item_name
                    pat = re.compile(f"({re.escape(watchlist_item)})", re.IGNORECASE)
                    highlight_name = re.sub(pat, "**\\1**", item_name)
                    
                    output.append('{} found in quest *{}*{}. Expires: {}. wowhead.com/quest={}'.format(highlight_name, quest_name, zone_names, quest_endtime_formatted, quest_id))                
    return output


def _checkForItem(item_id, wqs_data, items_to_check):
    # Takes an item id and looks up item in wqs_data. Returns the item name if it's in our list, otherwise returns False.
    patt = '_[' + str(item_id) + ']='
    item_start = wqs_data.index(patt) + len(patt)
    item_end = wqs_data.index(';', item_start)
    item_json = wqs_data[item_start:item_end]

    wqlist_item = json.loads(item_json)

    for item in items_to_check:
        if item.lower() in wqlist_item['name_enus'].lower():
            yield (wqlist_item['name_enus'], item)


def _lookupQuest(quest_id, wqs_data):
    # Takes a quest id and looks up quest in wqs_data. Returns quest name.
    patt = '_[' + str(quest_id) + ']='
    quest_start = wqs_data.index(patt) + len(patt)
    quest_end = wqs_data.index(';', quest_start)
    quest_json = wqs_data[quest_start:quest_end]

    quest = json.loads(quest_json)
    return quest['name_enus']


def _formatTime(time):
    return datetime.utcfromtimestamp(time/1000).strftime('%a, %m/%d at %I:%M %p')

#########################################################################


if __name__ == '__main__':
    import sys
    if not sys.argv[1:]:
        items = ['Bilewing', 'storm', 'glove']
        searchWQs(items=items)
    else:
        items = sys.argv[1:]
    print(searchWQs(items=items))
