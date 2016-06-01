### Usage


#### Import

	from mytarget import MyTargetClient


#### Init api client

	client_id = ''
	client_secret = ''

	mt = MyTargetClient(client_id, client_secret, is_sandbox=False)


#### Auth

	account = 'email@email.com'

	token_data = mt.oauth2.obtain_client_token(account)

	token = token_data['access_token']

	mt.auth(token)  # store token in requests.Session


#### Statistics

	date_from - date in format dd.mm.yyyy
	date_to - date in format dd.mm.yyyy

	banner_ids = [...]

	banner_stats = mt.statistics.banners(banner_ids, 'day', date_from=date_from, date_to=date_to)
