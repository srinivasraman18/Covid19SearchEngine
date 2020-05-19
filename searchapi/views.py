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
 
kw_extractor = yake.KeywordExtractor()


def is_similar(x,y):
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

	return cosine > 0.5


def faq_update(quest):
	flag=0
	contents=pd.read_csv('faqs.csv', index_col=0)
	if os.path.getsize('faqs.csv') > 1:
		for i, j in contents.iterrows():
			sim=is_similar(quest,j[0])
			if sim == True:
				flag=1
				count= int(j[1])
				count+=1
				contents.loc[i,'Count']=count	
		if flag==0:
			count=1
			new_row= pd.DataFrame([[quest,count]], columns=['Question','Count'])
			contents=contents.append(new_row,ignore_index=True)
		new_frame=contents.sort_values(['Count'], ascending=False)
		new_frame=new_frame.reset_index(drop=True)
		new_frame.to_csv('faqs.csv')	
				
	elif os.path.getsize('faqs.csv')<=1 :
		count=1
		new_entry= pd.DataFrame([[quest,count]], columns=['Question', 'Count'])
		new_entry.to_csv('faqs.csv')


	



def is_empty_csv(path):
	with open(path) as csvfile:
		reader = csv.reader(csvfile)
		for i, _ in enumerate(reader):
			if i:  # found the second row
				return False
	return True


def similar(keywords,quest):
	kw_extractor = yake.KeywordExtractor()
	list_=keywords.split(",")
	keywords1 = kw_extractor.extract_keywords(quest)
	klist=[]
	for k in keywords1:
		klist.append(k[1])
		list1_as_set = set(klist)
		intersection = list1_as_set.intersection(list_)
	if len(intersection)!=0:
		return 1
	else:
		return 0
		
def gettop3():
	contents=pd.read_csv('faqs1.csv')
	return contents['Question'].tolist()[:3]


def findsimilar(quest):
	flag=0
	similar_faqs = []
	if not is_empty_csv('faqs1.csv'):
		contents=pd.read_csv('faqs1.csv', index_col=0)

		
		count=0;
		q=""
		for i, j in contents.iterrows():
			keywords=j[1]
			ct=similar(keywords, quest)
			if ct!=0:
				similar_faqs.append(j[0])
				count=count+1
		if count==0:
			similar_faqs = gettop3()
		keywords = kw_extractor.extract_keywords(quest)
		kw=""
		for k in keywords:
			kw=kw+k[1]+","
		fg=contents[contents['Question']==quest.strip()]
		new_row= pd.DataFrame([[quest,kw[:len(kw)-1]]], columns=['Question','Keywords'])
		if fg.empty:
			new_row.to_csv('faqs1.csv', header=None, mode='a')
	else:
		keywords = kw_extractor.extract_keywords(quest)
		kw=""
		for k in keywords:
			kw=kw+k[1]+","
			new_entry= pd.DataFrame([[quest,kw[:len(kw)-1]]], columns=['Question','Keywords'])
			new_entry.to_csv('faqs1.csv')
	return similar_faqs




class FaqView(APIView):
	def get(self,request):
		df = pd.read_csv('faqs.csv')
		response_json = {}
		response_json["faqs"] = df['Question'].tolist()[:3]
		return Response(response_json)


class SearchView(APIView):
	def get(self,request):
		api_key = "AIzaSyCPbc8i_1wJhQK5MyuMucgwX4XSsJch2l8"
		resource = build("customsearch", 'v1', developerKey=api_key).cse()
		query = request.GET['query']
		response_json = {}
		fact_check = requests.get('https://factchecktools.googleapis.com/v1alpha1/claims:search',params = {'query':query,'key':api_key})
		if len(fact_check.json()['claims']) == 0:
			response_json['Common Myths'] = "No results Available"
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
		result = resource.list(q= query, cx='016284288800975862249:mj2ausqodab').execute()
		if len(result) == 0:
			response_json['News'] = "No results Available"
		else:
			url = None
			extractor = extractors.ArticleExtractor()
			response_json['News'] = []
			for item in result['items']:
				try:
					url = item['link']
					current_result = {}
					current_result['source'] = url
					current_result['content'] = []
					if url == 'https://www.cdc.gov/coronavirus/2019-ncov/faq.html' or url=='https://www.cdc.gov/coronavirus/2019-ncov/hcp/faq.html':
						page = requests.get("https://www.cdc.gov/coronavirus/2019-ncov/faq.html")
						soup = BeautifulSoup(page.content, 'html.parser')
						page_results= soup.find_all('div',attrs={'class': 'card bar'})
						for content in page_results:
							question = content.find('span',attrs = {'role':'heading'}).contents[0]
							answer = content.find('div',attrs = {'class':'card-body'}).contents[0]
							if is_similar(query,question):
								current_result['content'].append(answer)


					else:
						content = extractor.get_content_from_url(url)
						summary = summarize(content, ratio = 0.15)
						current_result['content'] = []
						current_result['content'].append(summary)
						response_json['News'].append(current_result)
				
				except TypeError:
					continue

		response_json["similar_questions"] = findsimilar(query)
		faq_update(query)
		return Response(response_json)

