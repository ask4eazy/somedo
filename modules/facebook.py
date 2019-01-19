#!/usr/bin/env python3

from datetime import datetime, timedelta
from time import sleep as tsleep
from random import uniform as runiform
from re import sub as rsub
from re import search as rsearch
from re import findall as rfindall
from base.chrometools import Chrome
from base.cutter import Cutter
from vis.netvis import NetVis

class Facebook:
	'Downloader for Facebook Accounts'

	ACCOUNT = ('type', 'id', 'name', 'path', 'link')
	ONEYEARAGO  = ( datetime.now() - timedelta(days=366) ).strftime('%Y-%m-%d')
	DEFAULTPAGELIMIT = 50
	DEFAULTNETWORKDEPTH = 1

	def __init__(self, job, storage, chrome, stop=None, headless=True, debug=False):
		'Generate object for Facebook by giving the needed parameters'
		self.storage = storage
		self.chrome = chrome
		self.stop = stop
		self.headless = headless
		self.options = job['options']
		self.ct = Cutter()
		self.emails = self.ct.split(job['login']['Email'])
		self.passwords = self.ct.split(job['login']['Password'])
		self.passwords += [ self.passwords[-1] for i in range(len(self.emails)-len(self.passwords)) ]	# same password
		if self.emails == [] or self.passwords == []:
			raise RuntimeError('At least one login account is needed for the Facebook module.')
		self.loginrevolver = -1	# for multiple investigator accounts
		errors = []	# to return error messages
		if debug:	# abort on errors in debug mode
			accounts = [ self.get_landing(i) for i in self.extract_paths(job['target']) ]	# get account infos with a first visit
			if self.options['Network']:
				self.get_network(accounts)
		else:	# be error robust on normal run
			accounts = []
			for i in self.extract_paths(job['target']):	# get account infos with a first visit
				try:
					account = self.get_landing(i)
				except:
					errors.append('Could not detect account "%s"' % i)
					continue
				accounts.append(account)
			if accounts == []:
				raise Exception('No valid target account(s) were detected.')
			if self.options['Network']:
				try:
					self.get_network(accounts)
				except:
					errors.append('Network')
		for i in accounts:	# go account after account
			for j in ('About', 'Photos', 'Timeline'):
				if self.chrome.stop_check():
					break
				if self.options[j]:
					cmd = 'self.get_%s(i)' % j.lower()
					if debug:
						exec(cmd)
					else:
						try:
							exec(cmd)
						except:
							errors.append(' %s:%s' %(i, j))
		self.chrome.close()
		if errors != []:
			raise Exception('The following Facebook account(s)/action(s) returned errors:'.join(errors)) 

	def sleep(self, t):
		'Sleep a slightly ranomized time'
		tsleep(t + runiform(0, 0.1))

	def extract_paths(self, target):
		'Extract facebook paths from target that might be urls'
		l= []	# list for the target users (id or path)
		for i in self.ct.split(target):
			i = rsub('^.*facebook.com/', '', i.rstrip('/'))
			i = rsub('&.*$', '', i)
			if i != '':
				l.append(i)
		return l

	def get_utc(self, date_str):
		'Convert date given as string (e.g. "2018-02-01") to utc as seconds since 01.01.1970'
		l = date_str.split('-')
		try:
			return int(datetime(int(l[0]),int(l[1]),int(l[2]),0,0).timestamp())
		except:
			return 0

	def get_profile_name(self, html):
		'Extract name'
		m = rsearch('>[^<]+</a>', html)
		if m != None:
			return m.group()[1:-4]
		m = rsearch('>[^<]+<span[^>]*>[^<]+</span>[^<]*</a>', html)
		if m != None:
			return rsub('<[^>]+>', '', m.group()[1:-4])
		return 'undetected'

	def extract_coverinfo(self):
		'Get information about given user (id or path) out of targeted profile cover'
		html = self.chrome.get_inner_html_by_id('fbProfileCover')
		if html == None:	# exit if no cover ProfileCover
			return None
		account = {'type': 'profile'}
		fid = self.ct.search(' data-referrerid="[0-9]+" ', html)	# try to get facebook id
		if fid == None:
			account['id'] = 'undetected'
		else:
			account['id'] = fid[18:-2]
		html = self.chrome.get_inner_html_by_id('fb-timeline-cover-name')
		account['name'] = self.get_profile_name(html)	# try to cut out displayed name (e.g. John McLane)
		html = self.chrome.get_inner_html_by_id('fbTimelineHeadline')	# try to get path
		path = self.ct.search(' data-tab-key="timeline" href="https://www\.facebook\.com/profile\.php\?id=[0-9]+', html)
		if path != None:
			account['path'] = path[71:]
		else:
			path = self.ct.search(' data-tab-key="timeline" href="https://www\.facebook\.com/[^"?/]+', html)
			if path == None:
				return None
			account['path'] = path[56:]
		account['link'] = 'https://facebook.com/' + account['path']
		return account

	def extract_sidebarinfo(self):
		'Get infos from entity_sidebar'
		html = self.chrome.get_outer_html_by_id('entity_sidebar')
		if html == None:	# exit if no cover entity_sidebar
			return None
		account = {'type': 'pg'}
		fid = self.ct.search(' aria-label="Profile picture" class="[^"]+" href="/[0-9]+', html)
		if fid != None:
			account['id'] = fid.rsplit('/', 1)[1]
		else:
			account['id'] = 'undetected'
		link = self.ct.search(' href="https://www\.facebook\.com/[^"/?]+', html)
		if link != None:
			account['path'] = link[32:]
			account['link'] = link[7:]
		elif fid != None:
			account['path'] = account['id']
			account['link'] = 'https://www.facebook.com/' + account['id']
		else:
			return None
		name = self.ct.search(' href="https://www\.facebook\.com/[^"]+"><span>[^<]+</span>', html)
		if name != None:
			account['name'] = name.rsplit('<', 2)[1][5:]
		else:
			account['name'] = 'undetected'
		return account

	def extract_leftcolinfo(self):
		'Get infos from leftCol'
		html = self.chrome.get_inner_html_by_id('leftCol')
		if html == None:	# exit if no cover entity_sidebar
			return None
		path = self.ct.search('<a href="/groups/[^/?"]+', html)
		if path == None:
			return None
		account = {'type': 'groups'}
		account['path'] = 'groups_' + path[17:]
		account['link'] = 'https://facebook.com' + path[9:]
		account['id'] = 'undetected'
		name = self.ct.search('<a href="/groups/[^"]+">[^<]+', html)
		if name != None:
			account['name'] = name.rsplit('"', 1)[1][1:]
		else:
			account['name'] = 'undetected'
		return account

	def extract_profileactions(self):
		'Get infos from pagelet_timeline_profile_actions'
		html = self.chrome.get_inner_html_by_id('pagelet_timeline_profile_actions')
		if html == None:	# exit if no profile actions
			return None
		html = self.ct.search('id&quot;:[0-9]+', html)
		if html == None:	# exit if no id was found
			return None
		return html[9:]

	def get_account(self, path):
		'Get account data and write information as CSV and JSON file if not alredy done'
		account = self.extract_coverinfo()	# try to get facebook id, path/url and name from profile page
		if account == None:
			account = self.extract_sidebarinfo()	# try to get account info from pg page
		if account == None:
			account = self.extract_leftcolinfo()	# try to get account info from groups etc.
		if account == None:
			return {
				'type': 'undetected', 
				'id': 'undetected',
				'name': 'undetected',
				'path': path.replace('/', '_'),
				'link': 'https://www.facebook.com/%s' % path
			}
		return account

	def link2account(self, html):
		'Extract account infos from Facebook link, e.g. in friend lists'
		if self.ct.search(' href="', html) == None:
			return None
		account = {'type': 'undetected'}
		for i in (	#	(regex, offset for account, account type)
			(' href="https://www\.facebook\.com/profile\.php\?id=[0-9]+', 47, 'profile'),
			(' href="https://www\.facebook\.com/pg/[^"/?]+', 35, 'pg'),
			(' href="https://www\.facebook\.com/groups/[^"/?]+', 39, 'groups'),
			(' href="https://www\.facebook\.com/[^"/?]+', 32, 'profile'),
			(' href="/profile\.php\?id=[0-9]+', 23, 'profile'),
			(' href="/pg/[^"/?]+', 11, 'pg'),
			(' href="/groups/[^"/?]+', 15, 'groups'),
			(' href="/[^"/?]+', 8, 'profile')
		):
			href = self.ct.search(i[0], html)
			if href != None:
				account['path'] = href[i[1]:]
				account['type'] = i[2]
				break
		if account['type'] == 'groups':
			account['link'] = 'https://www.facebook.com/groups/' + account['path']
			account['path'] = 'groups_' + account['path']
		else:
			account['link'] = 'https://www.facebook.com/' + account['path']
		fid = self.ct.search('id=[0-9]+', html)[3:]
		if fid != None:
			account['id'] = fid
		elif self.ct.search('[0-9]+', account['path']) == account['path']:	# path is facebook id?
			account['id'] = account['path']
		else:
			account['id'] = 'undetected'
		account['name'] = self.get_profile_name(html)
		return account

	def rm_pagelets(self):
		'Remove bluebar and other unwanted pagelets'
		self.chrome.rm_outer_html_by_id('pagelet_bluebar')
		self.chrome.rm_outer_html_by_id('pagelet_sidebar')
		self.chrome.rm_outer_html_by_id('pagelet_dock')
		self.chrome.rm_outer_html_by_id('pagelet_escape_hatch')	# remove "Do you know ...?"
		self.chrome.rm_outer_html_by_id('pagelet_ego_pane')	# remove "Suggested Groups"
		self.chrome.rm_outer_html_by_id('pagelet_rhc_footer')
		self.chrome.rm_outer_html_by_id('pagelet_page_cover')
		self.chrome.rm_outer_html_by_id('pagelet_timeline_composer')
		self.chrome.rm_outer_html_by_id('ChatTabsPagelet')
		self.chrome.rm_outer_html_by_id('BuddylistPagelet')
		self.chrome.rm_outer_html_by_id('PageComposerPagelet_')

	def rm_profile_cover(self):
		'Remove fbProfileCover'
		self.chrome.rm_outer_html_by_id('fbProfileCover')

	def rm_left(self):
		'Remove Intro, Photos, Friends etc. on the left'
		self.chrome.rm_outer_html('ClassName', '_1vc-')
		self.chrome.rm_outer_html_by_id('timeline_small_column')

	def rm_right(self):
		'Remove stuff right of timeline/posts'
		self.chrome.rm_outer_html_by_id('entity_sidebar')
		self.chrome.rm_outer_html_by_id('pages_side_column')
		self.chrome.rm_outer_html_by_id('rightCol')

	def rm_write_comment(self):
		'Remove Write a comment...'
		self.chrome.rm_outer_html('ClassName', 'UFIList')

	def click_translations(self):
		'Find the See Translation buttons and click'
		html = self.chrome.get_inner_html_by_id('recent_capsule_container')
		if html == None:
			html = self.chrome.get_inner_html_by_id('pagelet_timeline_main_column')
		if html == None:
			html = self.chrome.get_inner_html_by_id('pagelett_group_mall')
		if html == None:
			return
		for i in rfindall('<span id="translationSpinnerPlaceholder_[^"]+"', html):
			self.chrome.click_element_by_id(i[10:-1])

	def terminator(self):
		'Check date of posts to abort'
		if self.stop_utc <= 0:
			return False
		for i in self.chrome.get_outer_html('TagName', 'abbr'):
			m = rsearch(' data-utime="[0-9]+" ', i)
			try:
				if int(m.group()[13:-2]) <= self.stop_utc:
					return True
			except:
				pass
		return False

	def expand_page(self, path_no_ext='', expand=True, translate=False, until=ONEYEARAGO, limit=0):
		'Go through page, expand, translate, take screenshots and generate pdf'
		clicks = []
		if expand:	# clicks to expand page
			clicks.extend([
				['ClassName', 'see_more_link'],
				['ClassName', 'UFIPagerLink'],
				['ClassName', 'UFICommentLink'],
				['ClassName', ' UFIReplyList']
			])
		if translate:	# show translations if in options
			clicks.extend([
				['ClassName', 'UFITranslateLink']
			])
			action = self.click_translations()
		else:
			action = None
		self.stop_utc = until
		self.chrome.expand_page(
			path_no_ext = path_no_ext,
			click_elements_by = clicks,
			per_page_action = action,
			terminator=self.terminator,
			limit=limit
		)

	def account2html(self, account):
		'Write account info as html file'
		html = '<!doctype html>\n<html>\n<head>\n\t<title>Somed0 | Facebook Account | '
		html += account['name']
		html += '</title>\n\t<style type="text/css">\n\t\tbody {font-family: Sans-Serif;}\n\t</style>\n</head>\n<body>\n\t<h1>'
		html += account['name']
		html += '</h1><h2>Facebook ID: '
		html += account['id']
		html += ', Account Type: '
		html += account['type']
		html += '</h2>\n\t<h2>'
		html += account['link']
		html += '</h2>\n\t<h2><a href="'
		html += account['link']
		html += '" style="color: red; border-style: solid; padding: 0.2em;">Warning: Link to online Facebook account!!!</a>'
		html += '</h2></br>\n\t<img src="./account.png" alt="" style="border: solid;"\>\n</body>\n</html>'
		self.storage.write_xml(html, account['path'], 'account.html')

	def login(self):
		'Login to Facebook'
		if self.chrome.chrome_proc != None:
			self.chrome.close()
		self.chrome.open(stop=self.stop, headless=self.headless)
		self.chrome.navigate('https://www.facebook.com/login')	# go to facebook login
		if self.loginrevolver == -1:
				self.loginrevolver = 0
		for i in range(len(self.emails) * 10):	# try 10x all accounts
			if self.chrome.stop_check():
				return
			self.sleep(1)

			try:
				self.chrome.insert_element_by_id('email', self.emails[self.loginrevolver])	# login with email
				self.chrome.insert_element_by_id('pass', self.passwords[self.loginrevolver])	# and password
				self.chrome.click_element_by_id('loginbutton')	# click login
			except:
				pass
			else:
				self.sleep(1)
				if self.chrome.get_inner_html_by_id('findFriendsNav') != None:
					return
			self.loginrevolver += 1
			if self.loginrevolver == len(self.emails):
				self.loginrevolver = 0
		self.chrome.visible_page_png(self.storage.modpath('login'))
		raise Exception('Could not login to Facebook.')

	def navigate(self, url):
		'Navigate to given URL. Open Chrome/Chromium and/or login if needed'
		if self.chrome.chrome_proc == None:
			self.login()
		for i in range(10):
			for j in range(3):
				self.chrome.navigate(url)	# go to page
				self.sleep(1)
				try:
					m = rsearch('<img', self.chrome.get_inner_html_by_id('content'))
					if m != None:
						return
				except:
					pass
			self.login()
		raise Exception('Facebook might have blocked all given accounts.')

	def get_landing(self, path):
		'Get screenshot from start page about given user (id or path)'
		self.navigate('https://www.facebook.com/%s' % path)	# go to landing page of the given faebook account
		account = self.get_account(path)	# get account infos if not already done
		self.storage.mksubdir(account['path'])	# as landing is the first task to perform, generate the subdiroctory here
		self.storage.write_dicts(account, self.ACCOUNT, account['path'], 'account.csv')	# write account infos
		self.storage.write_json(account, account['path'], 'account.json')
		try:	# try to download profile photo
			self.storage.download(self.ct.src(self.chrome.get_inner_html_by_id('fbTimelineHeadline')), account['path'], 'profile.jpg')
		except:
			pass
		self.rm_pagelets()	# remove bluebar etc.
		if account['type'] == 'pg':
			self.rm_write_comment()
		path_no_ext = self.storage.modpath(account['path'], 'account')	# generate a file path for screenshot and pdf
		self.chrome.visible_page_png(path_no_ext)	# save the visible part of the page as png
		self.chrome.page_pdf(path_no_ext)	# and as pdf (when headless)
		self.account2html(account)
		return account	# give back the targeted account

	def get_timeline(self, account):
		'Get timeline'
		if account['type'] == 'pg':
			self.navigate('https://www.facebook.com/pg/%s/posts' % account['path'])
			path_no_ext = self.storage.modpath(account['path'], 'posts')
		else:
			self.navigate(account['link'])
			path_no_ext = self.storage.modpath(account['path'], 'timeline')
		self.rm_profile_cover()
		self.rm_pagelets()
		self.rm_left()
		self.rm_right()
		self.expand_page(	# go through timeline
			path_no_ext=path_no_ext,
			limit=self.options['limitTimeline'],
			until=self.options['untilTimeline'],
			expand=self.options['expandTimeline'],
			translate=self.options['translateTimeline']
		)
		self.chrome.page_pdf(path_no_ext)
		if self.options['Network'] and self.options['depthNetwork']:
			return self.get_visitors(account)
		else:
			return None

	def get_visitors(self, account):
		'Get all visitors who left comments or likes etc. in timeline - timeline has to be open end expand'
		visitors = []	# list to store links to other profiles
		visitor_ids = {account['id']}	# create set to store facebook ids of visitors to get uniq visitors
		items = self.chrome.get_outer_html('ClassName', 'commentable_item')	# get commentable items
		for i in items:
			for j in rfindall('<a class="[^"]+" data-hovercard="/ajax/hovercard/user\.php\?id=[^"]+" href="[^"]+"[^>]*>[^<]+</a>', i):	# get comment authors
				visitor = self.link2account(j)
				if not visitor['id'] in visitor_ids:	# uniq
					visitors.append(visitor)
					visitor_ids.add(visitor['id'])
			href = self.ct.search('href="/ufi/reaction/profile/browser/[^"]+', i)		# get reactions
			if href != None:
				if self.chrome.stop_check():
					return
				self.navigate('https://www.facebook.com' + href[6:])	# open reaction page
				self.chrome.expand_page(terminator=self.terminator)	# scroll through page
				self.rm_pagelets()	# remove bluebar etc.
				html = self.chrome.get_inner_html_by_id('content')	# get the necessary part of the page
				for j in rfindall(
					' href="https://www\.facebook\.com/[^"]+" data-hovercard="/ajax/hovercard/user\.php\?id=[^"]+" data-hovercard-prefer-more-content-show="1"[^<]+</a>',
					html
				):
					visitor = self.link2account(j)
					if visitor != None and not visitor['id'] in visitor_ids:	# uniq
						visitors.append(visitor)
						visitor_ids.add(visitor['id'])
		self.storage.write_2d([ [ i[j] for j in self.ACCOUNT ] for i in visitors ], account['path'], 'visitors.csv')
		self.storage.write_json(visitors, account['path'], 'visitors.json')
		return { i['path'] for i in visitors }	# return visitors ids as set

	def get_about(self, account):
		'Get About'
		self.navigate('%s/about' % account['link'])	# go to about
		path_no_ext=self.storage.modpath(account['path'], 'about')
		self.rm_pagelets()	# remove bluebar etc.
		self.expand_page(path_no_ext=path_no_ext)
		self.chrome.page_pdf(path_no_ext)

	def get_photos(self, account):
		'Get Photos'
		if account['type'] == 'pg':
			self.navigate('https://www.facebook.com/pg/%s/photos' % account['path'])
		elif account['type'] == 'groups':
			self.navigate(account['link'] + '/photos')
		else:
			self.navigate(account['link'] + '/photos_all')
		path_no_ext = self.storage.modpath(account['path'], 'photos')
		self.rm_pagelets()	# remove bluebar etc.
		self.rm_right()
		self.expand_page(path_no_ext=path_no_ext, limit=self.options['limitPhotos'])
		self.rm_left()
		self.chrome.page_pdf(path_no_ext)
		cnt = 1	# to number screenshots
		if account['type'] == 'pg':
			html = self.chrome.get_inner_html_by_id('content_container')
			if html != None:
				for i in rfindall('<a href="https://www\.facebook\.com/[^"]+/photos/[^"]+" rel="theater">', html):
					if self.chrome.stop_check():
						return
					self.navigate(i[9:-16])
					self.chrome.rm_outer_html_by_id('photos_snowlift')	# show page with comments
					path_no_ext = self.storage.modpath(account['path'], '%05d_photo' % cnt)
					self.rm_pagelets()	# remove bluebar etc.
					self.expand_page(
						path_no_ext=path_no_ext,
						limit=self.options['limitPhotos'],
						expand=self.options['expandPhotos'],
						translate=self.options['translatePhotos']
					)
					self.chrome.page_pdf(path_no_ext)
					try:
						self.storage.download(
							self.ct.src(self.chrome.get_outer_html('ClassName', 'scaledImageFitWidth img')[0]),
							account['path'],
							'%05d_image.jpg' % cnt
						)
					except:
						pass
					cnt += 1
					if cnt == 100000:
						break
					self.chrome.go_back()
		elif account['type'] == 'groups':
			html = self.chrome.get_inner_html_by_id('pagelet_group_photos')
			if html != None:
				for i in rfindall(' href="https://www.facebook.com/photo\.php\?[^"]+', html):
					if self.chrome.stop_check():
						return
					self.navigate(i[7:])
					self.chrome.rm_outer_html_by_id('photos_snowlift')	# show page with comments
					path_no_ext = self.storage.modpath(account['path'], '%05d_photo' % cnt)
					self.rm_pagelets()	# remove bluebar etc.
					self.expand_page(
						path_no_ext=path_no_ext,
						limit=self.options['limitPhotos'],
						expand=self.options['expandPhotos'],
						translate=self.options['translatePhotos']
					)
					self.chrome.page_pdf(path_no_ext)
					try:
						self.storage.download(
							self.ct.src(self.chrome.get_outer_html('ClassName', 'scaledImageFitWidth img')[0]),
							account['path'],
							'%05d_image.jpg' % cnt
						)
					except:
						pass
					cnt += 1
					if cnt == 100000:
						break
					self.chrome.go_back()
		else:
			html = self.chrome.get_inner_html_by_id('pagelet_timeline_medley_photos')
			if html != None:
				for i in rfindall('ajaxify="https://www\.facebook\.com/photo\.php?[^"]*"', html):	# loop through photos
					if self.chrome.stop_check():
						return
					self.navigate(i[9:-1])
					self.chrome.rm_outer_html_by_id('photos_snowlift')	# show page with comments
					path_no_ext = self.storage.modpath(account['path'], '%05d_photo' % cnt)
					self.rm_pagelets()	# remove bluebar etc.
					self.expand_page(
						path_no_ext=path_no_ext,
						limit=self.options['limitPhotos'],
						expand=self.options['expandPhotos'],
						translate=self.options['translatePhotos']
					)
					self.chrome.page_pdf(path_no_ext)
					try:
						self.storage.download(
							self.ct.src(self.chrome.get_outer_html('ClassName', 'scaledImageFitWidth img')[0]),
							account['path'],
							'%05d_image.jpg' % cnt
						)
					except:
						pass
					cnt += 1
					if cnt == 100000:
						break
					self.chrome.go_back()

	def get_friends(self, account):
		'Get friends list from given user (id or path)'
		if account['type'] == 'profile':
			self.navigate('%s/friends' % account['link'])
			path_no_ext = self.storage.modpath(account['path'], 'friends')
			self.rm_pagelets()	# remove bluebar etc.
			self.rm_left()
			self.chrome.expand_page(path_no_ext=path_no_ext)	# no limit for friends - it makes no sense not getting all friends
			self.chrome.page_pdf(path_no_ext)
			html = self.chrome.get_inner_html_by_id('pagelet_timeline_medley_friends')	# try to get friends
			if html == None:
				return []	# return empty list if no visible friends
			flist = []	# list to store friends
			for i in rfindall(' href="https://www\.facebook\.com\/[^<]+=friends_tab" [^<]+</a>', html):	# get the links to friends
				friend = self.link2account(i)
				if friend != None:
					flist.append(friend)	# append to friend list if info was extracted
			self.storage.write_2d([ [ i[j] for j in self.ACCOUNT] for i in flist ], account['path'], 'friends.csv')
			self.storage.write_json(flist, account['path'], 'friends.json')
			return { i['path'] for i in flist }	# return friends as set
		if account['type'] == 'groups':
			self.navigate('%s/members' % account['link'])
			path_no_ext = self.storage.modpath(account['path'], 'members')
			self.rm_pagelets()	# remove bluebar etc.
			self.rm_right()
			self.chrome.set_x_left()
			self.chrome.expand_page(path_no_ext=path_no_ext)	# no limit for friends - it makes no sense not getting all friends
			self.rm_left()
			self.chrome.page_pdf(path_no_ext)
			html = self.chrome.get_inner_html_by_id('groupsMemberBrowser')	# try to get members
			if html == None:
				return []	# return empty list if no visible friends
			mlist = []	# list to store friends
			for i in rfindall(' href="https://www\.facebook\.com\/[^<]+location=group" [^<]+</a>', html):	# regex vs facebook
				member = self.link2account(i)
				if member != None:
					mlist.append(member)	# append to friend list if info was extracted
			self.storage.write_2d([ [ i[j] for j in self.ACCOUNT] for i in mlist ], account['path'], 'members.csv')
			self.storage.write_json(mlist, account['path'], 'members.json')
			return { i['path'] for i in mlist }	# return members as set
		return set()

	def get_network(self, accounts):
		'Get friends and friends of friends and so on to given depth or abort if limit is reached'
		network = dict()	# dictionary to store friend lists
		old_ids = set()	# set to store ids already got handled
		all_ids = set() # set for all ids
		for i in accounts:	# start with the given target accounts
			if self.chrome.stop_check():
				break
			friends = self.get_friends(i)
			network.update({i['path']: {	# add friends
				'id': i['id'],
				'type': i['type'],
				'name': i['name'],
				'link': i['link'],
				'friends': friends
			}})
			old_ids.add(i['path'])	# remember already handled accounts
			all_ids.add(i['path'])	# update set of all ids
			all_ids |= friends
			if self.options['extendNetwork']:	# also add visitors to network if desired
				visitors = self.get_timeline(i)
				self.options['Timeline'] = False	# on extendNetwork no extra Timeline visit is needed
				network[i['path']]['visitors'] = visitors
				all_ids |= visitors
			else:
				network[i['path']]['visitors'] = set()	# empty set if extended option is false
		if self.options['depthNetwork'] > 0:	# on 0 only get friend list(s)
			depth = self.options['depthNetwork']
		else:
			return
		for i in range(depth):	# stay in depth limit and go through friend lists
			if self.chrome.stop_check():
				break
			for j in all_ids - old_ids:	# work on friend list which have not been handled so far
				account = self.get_landing(j)
				self.sleep(5)
				network.update({account['path']: {	# add new account
					'id': account['id'],
					'type': account['type'],
					'name': account['name'],
					'link': account['link'],
					'friends': set(),
					'visitors': set()
				}})
				if i < depth - 1:	# on last recusion level do not get the friend lists anymore
					if self.chrome.stop_check():
						break
					network[j]['friends'] = self.get_friends(account)
					if extended:
						network[j]['visitors'] = self.get_timeline(
							i,
							expand=True,
							translate=False,
							visitors=True,
							until=0,
							limit=limit,
							dontsave=True
						)
					else:
						network[j]['visitors'] = set()
		netvis = NetVis(self.storage)	# create network visualisation object
		friend_edges = set()	# generate edges for facebook friends excluding doubles
		for i in network:
			netvis.add_node(
				i,
				image = '../%s/profile.jpg' % i,
				alt_image = './pixmaps/profile.jpg',
				label = network[i]['name'],
				title = '<img src="../%s/account.png" alt="%s" style="width: 24em;"/>' % (i, i)
			)
			for j in network[i]['friends']:
				if not '%s %s' % (i, j) in friend_edges:
					friend_edges.add('%s %s' % (j, i))
		for i in friend_edges:
			ids = i.split(' ')
			netvis.add_edge(ids[0], ids[1])
		if extended:	# on extended create edges for the visitors as arrows
			visitor_edges = { '%s %s' % (j, i) for i in network for j in network[i]['visitors'] }
			for i in visitor_edges:
				ids = i.split(' ')
				netvis.add_edge(ids[0], ids[1], arrow=True, dashes=True)
		netvis.write(doubleclick="window.open('../' + params.nodes[0] + '/account.html')")
