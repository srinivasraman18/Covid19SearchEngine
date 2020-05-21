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
 
kw_extractor = yake.KeywordExtractor()


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
			if sim==True:
				key_list1=process(key_list)
				compare_list=process(eval(j[2]))
				if find_similarity(key_list1,compare_list):
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
		response_json["faqs"] = df['Question'].tolist()[:3]
		return Response(response_json)


class SearchView(APIView):
	def get(self,request):
		api_key = "AIzaSyCPbc8i_1wJhQK5MyuMucgwX4XSsJch2l8"
		search_engine_id = "016284288800975862249:mj2ausqodab"
		#api_key = "AIzaSyBUOR1z8vQaKwnS0vbS5dLK7GZUB20j99w"
		#search_engine_id = "016400685532725398485:nojhx1tdntd"
		resource = build("customsearch", 'v1', developerKey=api_key).cse()
		query = request.GET['query']
		response_json = {}
		fact_check = requests.get('https://factchecktools.googleapis.com/v1alpha1/claims:search',params = {'query':query,'key':api_key})
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
		result = resource.list(q= query, cx = search_engine_id).execute()
		if len(result) == 0:
			response_json['News'] = [{'source':'No Results Available for this query','content':'Not Available'}]
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
							if is_similar(query,question,0.5):
								current_result['content'].append(answer)


					else:
						content = extractor.get_content_from_url(url)
						summary = summarize(content, ratio = 0.15)
						current_result['content'] = []
						current_result['content'].append(summary)
						response_json['News'].append(current_result)
				
				except TypeError:
					continue

		update_faq(query)
		response_json["similar_questions"] = related_questions(query)
		return Response(response_json)

