from oauth2client.file import Storage
import httplib2
import urllib
import json
from datetime import datetime, timedelta

# Your acount needs to be authorized for these requests. Get an API key and then an OAuth 2 client ID
# from console.developers.google.com, then use oauth2client to generate some credentials.
# instructions here: https://developers.google.com/api-client-library/python/guide/aaa_oauth
storage = Storage('credentials.dat')
credentials = storage.get()
http = credentials.authorize(httplib2.Http())

# Exception for unexpected responses from YouTube's API
class APIException(Exception):
	def __init__(self, message, headers, content):
		super(APIException, self).__init__(message)
		self.headers = headers
		self.content = content

# Sends a reportAbuse query with all the required parameters. Note: depending on your credentials.dat, your access to this API will be severely limited unless your account has TRUSTED_FLAGGER status.
def report(video_id, reason_id, sec_reason_id, comment):
	resp, content = http.request("https://www.googleapis.com/youtube/v3/videos/reportAbuse", "POST", body=json.dumps({"videoId": video_id,"reasonId": reason_id, "secondaryReasonId": sec_reason_id, "comments": comment}), headers={'Content-Type': 'application/json'})
	if resp['status'] == '204':
		return True
	elif resp['status'] == '404':
		return False
	elif resp['status'].startswith('5'):
		return report(video_id, reason_id, sec_reason_id, comment)
	else:
		raise APIException("Unexpected response from reportAbuse: {}".format(resp["status"]), resp, content)

# report wrapper for phishing videos
def report_phishing(video_id, comment):
	return report(video_id, "S", "29", comment)

# report wrapper for mass-advertising videos
def report_spam(video_id, comment):
	 return report(video_id, "S", "27", comment)


# Search on youtube. Takes a dict of API parameters, returns a dict of videos. max_pages can be overridden for more or less results (50 per page - max allowed by API)
def search(params, max_pages=10):
	p = {'maxResults': 50, 'safeSearch': 'none', 'part': 'snippet'}
	p.update(params)
	resp, content = http.request("https://www.googleapis.com/youtube/v3/search?{}".format(urllib.urlencode(p).replace("%22", '"')), "GET")
	if resp["status"] == '200' and resp["content-type"].split(';')[0] == "application/json":
		j = json.loads(content)
		if "nextPageToken" in j and max_pages > 1:
			params["pageToken"] = j["nextPageToken"]
			return j["items"] + search(params, max_pages - 1)
		else:
			return j["items"]
	elif resp["status"] == '204' or resp["status"].startswith('5'):
		return search(params, max_pages)
	else:
		raise APIException("Unexpected response from search: {}".format(resp["status"]), resp, content)

# Get the display info of a channel from its ID.
def get_channel_info(channel_id):
	p = {'id': channel_id, 'part': 'snippet'}
	resp, content = http.request("https://www.googleapis.com/youtube/v3/channels?{}".format(urllib.urlencode(p)), "GET")
	if resp["status"] == '200' and resp["content-type"].split(';')[0] == "application/json":
		j = json.loads(content)
		if len(j["items"]) == 0:
			return None
		if len(j["items"]) > 1:
			raise APIException("Unexpected response from channel lookup by id: got {} results, expected 0 or 1".format(len(j["items"])), resp, content)
		return j["items"][0]
	elif resp["status"] == '204' or resp["status"].startswith('5'):
		return get_channel_info(channel_id)
	else:
		raise APIException("Unexpected response from channel lookup by id: {}".format(resp["status"]), resp, content)

# Get all the videos from a channel.
def get_channel_videos(channel_id):
	return [v for v in search({'channelId': channel_id, 'order': 'date'}) if v['id']['kind'] == 'youtube#video']

# Searches a term with the upload filter of "Last Hour".
def search_last_hour(term):
	d = datetime.utcnow() - timedelta(hours=1)
	isotime = "{:0>4d}-{:0>2d}-{:0>2d}T{:0>2d}:{:0>2d}:{:0>2d}Z".format(d.year, d.month, d.day, d.hour, d.minute, d.second)
	return search({"q": term, "publishedAfter": isotime})

# Searches a term with the upload filter of "Today".
def search_last_day(term):
        d = datetime.utcnow() - timedelta(days=1)
        isotime = "{:0>4d}-{:0>2d}-{:0>2d}T{:0>2d}:{:0>2d}:{:0>2d}Z".format(d.year, d.month, d.day, d.hour, d.minute, d.second)
        return search({"q": term, "publishedAfter": isotime})

# Get a list of videos' metadata and content details by ids. May not return all of the specified elements, if an ID isn't found or has been terminated.
def get_videos(id_list):
	rest = None
	if len(id_list) > 50: # 50 is the max we can pass to this API call at once
		rest = id_list[50:]
		id_list = id_list[:50]
	p = {'id': ','.join(id_list), 'part': 'snippet,contentDetails'}
	resp, content = http.request("https://www.googleapis.com/youtube/v3/videos?{}".format(urllib.urlencode(p)), "GET")
	if resp["status"] == '200' and resp["content-type"].split(';')[0] == "application/json":
		j = json.loads(content)
		if rest:
			return j["items"] + get_videos(rest)
		else:
			return j["items"]
	elif resp["status"] == '204' or resp["status"].startswith('5'):
		if rest:
			return get_videos(id_list) + get_videos(rest)
		else:
			return get_videos(id_list)
	else:
		raise APIException("Unexpected response from video lookup: {}".format(resp["status"]), resp, content)

# Convenience/legacy method for getting metadata for one video ID. If you have multiple IDs to get, it's preferable to use get_videos to put them all in one API request.
def get_video(video_id):
	return get_videos([video_id])

# Get the first 100 CommentThreads on a video (a CommentThread is a top-level video comment which can have replies, hence the method name)
# 100 is the max per API call - didn't want to increase this for now in case we scan videos with many thousands of comments...
def get_comments(video_id):
	p = {'videoId': video_id, 'part': 'snippet', 'maxResults': '100'}
	resp, content = http.request("https://www.googleapis.com/youtube/v3/commentThreads?{}".format(urllib.urlencode(p)), "GET")
	if resp["status"] == '200' and resp["content-type"].split(';')[0] == "application/json":
		return json.loads(content)["items"]
	elif resp["status"] == '204' or resp["status"].startswith('5'):
		return get_comments(video_id)
	elif resp["status"] == '403':
		return [] # comments disabled on video
	else:
		raise APIException("Unexpected response from comment lookup: {}".format(resp["status"]), resp, content)
