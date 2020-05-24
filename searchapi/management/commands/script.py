import requests
import pymongo
from django.core.management.base import BaseCommand, CommandError



class Command(BaseCommand):

	def handle(self,*args, **options):
		state_level_v2 = requests.get('https://api.covid19india.org/v2/state_district_wise.json').json()
		national_level = requests.get(' https://api.covid19india.org/data.json').json()
		state_level_changes = requests.get('https://api.covid19india.org/states_daily.json').json()
		#district_level_changes = requests.get('https://api.covid19india.org/districts_daily.json').json()
		zones = requests.get('https://api.covid19india.org/zones.json').json()
		client = pymongo.MongoClient("mongodb+srv://srinivasraman18:Covid19@cluster0-m2iml.mongodb.net/test?retryWrites=true&w=majority")
		mydb = client["covid19"]
		mydb["state_level_v2"].remove({})
		mydb["national_level"].remove({})
		mydb["state_level_changes"].remove({})
		mydb["zones"].remove({})
		mydb["state_level_v2"].insert_many(state_level_v2)
		mydb["national_level"].insert_one(national_level)
		mydb["state_level_changes"].insert_one(state_level_changes)
		mydb["zones"].insert_one(zones)
		return
