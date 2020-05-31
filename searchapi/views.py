from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apiclient.discovery import build
from boilerpy3 import extractors
from gensim.summarization.summarizer import summarize 
import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize 
from csv import reader, writer
import os
import pandas as pd
import yake
import csv
from nltk import LancasterStemmer
import pymongo
import time
import copy
import urllib
import re
import sys
kw_extractor = yake.KeywordExtractor()
client = pymongo.MongoClient("mongodb+srv://srinivasraman18:Covid19@cluster0-m2iml.mongodb.net/test?retryWrites=true&w=majority")


def is_similar(x,y,threshold = 0.5):
	X_list = word_tokenize(x)  
	Y_list = word_tokenize(y) 
	sw = stopwords.words('english')  
	l1 =[];l2 =[] 
	X_set = {w for w in X_list if not w in sw}  
	Y_set = {w for w in Y_list if not w in sw} 
	   
	rvector = X_set.union(Y_set)  
	for w in rvector: 
		if w in X_set: l1.append(1) 
		else: l1.append(0) 
		if w in Y_set: l2.append(1) 
		else: l2.append(0) 
	c = 0
	for i in range(len(rvector)): 
			c+= l1[i]*l2[i] 
	cosine = c / float((sum(l1)*sum(l2))**0.5) 

	return cosine >= threshold



def find_similarity(list1, list2):
	intersection = list(set(list1)&set(list2))
	if len(intersection)==0: #can be changed when population of CSV becomes larger to limit number of questions returned
		return 0
	else:
		return 1


def process(word_list):
	lancaster=LancasterStemmer()
	new_list=[]
	for word in word_list:
		w=lancaster.stem(word)
		new_list.append(w)
	return new_list

def related_questions(quest):
	keywords = kw_extractor.extract_keywords(quest)
	key_list=[]
	for k in keywords:
		key_list.append(k[1])
	key=str(key_list)

	list_of_rel_q=[]


	flag=0
	contents=pd.read_csv('faqs.csv', index_col=0)
	if os.path.getsize('faqs.csv') > 1:
		for i, j in contents.iterrows():
			sim=is_similar(quest,j[0],1)
			if sim==False:
				key_list1=process(key_list)
				compare_list=process(eval(j[2]))
				if find_similarity(key_list1,compare_list) == 1:
					list_of_rel_q.append(j[0])
					flag=1
						
		if flag==0:
			i=0
			while i<3:
				list_of_rel_q.append(contents.loc[i,'Question'])
				i+=1
	return list_of_rel_q


def update_faq(quest):
	keywords = kw_extractor.extract_keywords(quest)
	key_list=[]
	for k in keywords:
		key_list.append(k[1])
	key=str(key_list)
	flag=0
	contents=pd.read_csv('faqs.csv', index_col=0)
	if os.path.getsize('faqs.csv') > 1:
		for i, j in contents.iterrows():
			sim=is_similar(quest,j[0],0.5)
			if sim == True:
				flag=1
				count= int(j[1])
				count+=1
				contents.loc[i,'Count']=count	
		if flag==0:
			count=1
			new_row= pd.DataFrame([[quest,count,key]], columns=['Question','Count','Keywords'])
			contents=contents.append(new_row,ignore_index=True)
		new_frame=contents.sort_values(['Count'], ascending=False)
		new_frame=new_frame.reset_index(drop=True)
		new_frame.to_csv('faqs.csv')	
				
	elif os.path.getsize('faqs.csv')<=1 :
		count=1
		new_entry= pd.DataFrame([[quest,count,key]], columns=['Question', 'Count','Keywords'])
		new_entry.to_csv('faqs.csv')

class FaqView(APIView):
	def get(self,request):
		df = pd.read_csv('faqs.csv')
		response_json = {}
		response_json["faqs"] = df['Question'].tolist()[:5]
		return Response(response_json)


class SearchView(APIView):
	def get(self,request):
		api_key = os.environ["API_KEY"]
		search_engine_id = os.environ["SEARCH_ENGINE_ID"]
		resource = build("customsearch", 'v1', developerKey=api_key).cse()
		query = request.GET['query']
		query = query.lower()
		query = re.sub(r'[^\w\s]','',query)
		response_json = {}
		fact_check = requests.get('https://factchecktools.googleapis.com/v1alpha1/claims:search',params = {'query':query,'key':api_key,'languageCode':'en-US'})
		db = client["news"]
		if len(fact_check.json()) == 0:
			response_json['Common Myths'] = [{'source':'No Results Available for this query','check':'Not Available','claim':'Not Available'}]

		else:
			claims = fact_check.json()['claims']
			ratings = [claims[i]['claimReview'][0]['textualRating'] for i in range(0,len(claims))]
			factcheck = None
			for rating in ratings:
				if rating == 'False' or 'myth' in rating or 'no evidence' in rating:
					factcheck = False
					
			if factcheck == False:
				response_json['Common Myths'] = []
				for claim in claims:
					current_result = {}
					current_result['source'] = claim['claimReview'][0]['url']
					current_result['check'] = claim['claimReview'][0]['textualRating']
					current_result['claim'] = claim['text']
					response_json['Common Myths'].append(current_result)

			else:
				response_json['Common Myths'] = [{'source':'No Results Available for this query','check':'Not Available','claim':'Not Available'}]
		result = resource.list(q= query, cx = search_engine_id).execute()
		stored_queries = db["news"].find({'_id':query})
		stored_result = []
		for q in stored_queries:
			stored_result.append(q)
		is_stored = None
		if len(stored_result)==0:	
			is_stored = False
		else:
			is_stored = True
		if len(result) == 0 or 'items' not in result:
			response_json['News'] = [{'source':'No Results Available for this query','content':'Not Available'}]
		else:
			url = None
			extractor = extractors.ArticleExtractor()
			response_json['News'] = []
			if is_stored == False:
				for item in result['items']:
					try:
						url = item['link']
					
						
						if url == 'https://www.cdc.gov/coronavirus/2019-ncov/faq.html' or url=='https://www.cdc.gov/coronavirus/2019-ncov/hcp/faq.html':
							page = requests.get("https://www.cdc.gov/coronavirus/2019-ncov/faq.html")
							soup = BeautifulSoup(page.content, 'html.parser')
							page_results= soup.find_all('div',attrs={'class': 'card bar'})
							for content in page_results:
								question = content.find('span',attrs = {'role':'heading'}).contents[0]
								question = question.lower()
								re.sub(r'[^\w\s]','',question)
								question = question
								answer = content.find('div',attrs = {'class':'card-body'}).find('p').getText()
								
								if len(answer)!=0 and is_similar(query,question,0.5):
									current_result = {}
									current_result['source'] = url
									current_result['content'] = []
									print(question,":",answer)
									current_result['content'].append(answer)
									response_json['News'].append(current_result)

							


						else:
							response = requests.get(url)
							content = extractor.get_content(response.text)
							summary = summarize(content, ratio = 0.15)
							current_result = {}
							current_result['source'] = url
							current_result['content'] = []
							current_result['content'].append(summary)
							if 'Last-Modified' in response.headers:
								current_result['last_modified'] = response.headers['Last-Modified']
							else:
								current_result['last_modified'] = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.gmtime())

							response_json['News'].append(current_result)
					

					except urllib.error.HTTPError as e:
						current_result['content'] = ["No results available"]
						continue

					except TypeError:
						current_result['content'] = ["No results available"]
						continue

					except AttributeError:
						current_result['content'] = ["No results available"]
						continue
					

				db_json = {}
				db_json['News'] = response_json['News']
				for i,news in enumerate(db_json['News']):
					url = news['source']
					response = requests.get(url,verify=False)
					headers = response.headers
					last_modified = None
					if 'Last-Modified' in headers:
						last_modified = headers['Last-Modified']
					else:
						last_modified = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.gmtime()) 
					db_json['News'][i]['last_modified'] = last_modified
					
				db_json['News'] = [[json] for json in db_json['News']]
				db_json['_id'] = query
				db["news"].insert_one(db_json)


			else:

				#print("Stored Result",stored_result)
				query_json= stored_result[0]
				stored_sources = []
				for news in query_json["News"]:
					news_dict = news[-1]
					response = requests.get(news_dict["source"])
					stored_sources.append(news_dict["source"])
					if 'Last-Modified' in response.headers:
						if time.strptime(response.headers['Last-Modified'],"%a, %d %b %Y %H:%M:%S %Z") > time.strptime(news_dict['last_modified'],"%a, %d %b %Y %H:%M:%S %Z"):
							current_result = {}
							content = extractor.get_content(response.text)
							summary = summarize(content, ratio = 0.15)
							current_result['content'] = []
							current_result['content'].append(summary)
							current_result['source'] = news_dict["source"]
							current_result['last_modified'] = response.headers['Last-Modified']
							news.append(current_result)

					else:
						stored_content = news_dict["content"]
						content = extractor.get_content(response.text)
						summary = summarize(content, ratio = 0.15)
						if stored_content[0] != summary:
							current_result = {}
							current_result['content'] = []
							current_result['content'].append(summary)
							current_result['source'] = news_dict["source"]
							current_result['last_modified'] = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.gmtime())
							news.append(current_result)
				
				for item in result['items']:
					try:
						if item['link'] not in stored_sources:
							url = item['link']
							current_result = {}
							current_result['source'] = url
							current_result['content'] = []
				
							response = requests.get(url)
							content = extractor.get_content(url.text)
							summary = summarize(content, ratio = 0.15)
							current_result['content'].append(summary)
							if 'Last-Modified' in response.headers:
								current_result['last_modified'] = response.headers['Last-Modified']
							else:
								current_result['last_modified'] = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.gmtime())
							query_json['News'].append([current_result])



					
					except urllib.error.HTTPError as e:
						current_result['content'] = ["No results available"]
						continue

					except TypeError:
						current_result['content'] = ["No results available"]
						continue

					except AttributeError:
						current_result['content'] = ["No results available"]
						continue


					db["news"].save(query_json)
					

					response_json["News"] = []
					for news in query_json["News"]:
						latest_news = news[-1]
						current_dict = {}
						current_dict["source"] = latest_news["source"]
						current_dict["content"] = latest_news["content"]
						response_json["News"].append(current_dict)
					



		update_faq(query)
		response_json["similar_questions"] = related_questions(query)
		return Response(response_json)



class StatisticsView(APIView):
	def get(self,request):
		mydb = client["covid19"]
		state_level_v2 = mydb["state_level_v2"].find({},{'_id': 0})
		national_level = mydb["national_level"].find({},{'_id': 0})
		state_level_changes = mydb["state_level_changes"].find({},{'_id': 0})
		zones = mydb["zones"].find({},{'_id': 0})

		state_level_v2 = [result for result in state_level_v2]
		national_level = [result for result in national_level][0]
		state_level_changes = [result for result in state_level_changes][0]
		zones = [result for result in zones][0]

		national_level_dict = {}
		for state in national_level["statewise"]:
			national_level_dict[state["statecode"]] = state
		state_level_changes_dict = dict(state_level_changes["states_daily"][-1])
		"""district_level_changes_dict = {}
		for state,state_value in district_level_changes["districtsDaily"].items():
		  for district,dist_vals in state_value.items():
			district_level_changes_dict[district] = dist_vals[-1]"""
		zone_dict = {}
		for district_info in zones["zones"]:
			zone_dict[district_info["district"]] = district_info
		response_json = state_level_v2

		for i,state in enumerate(response_json):
			state_code = state['statecode']
			if state_code not in national_level_dict or state_code.lower() not in state_level_changes_dict:
				del response_json[i]
				continue
			response_json[i]['state_case_info'] = national_level_dict[state_code]
			response_json[i]['state_level_changes'] = state_level_changes_dict[state_code.lower()]
			for j,district in enumerate(state['districtData']):
				if district['district'] not in zone_dict or district['district'] not in zone_dict: 
					del response_json[i]['districtData'][j]
					continue
				response_json[i]['districtData'][j]['zone'] = zone_dict[district['district']]['zone']

		return Response(response_json)