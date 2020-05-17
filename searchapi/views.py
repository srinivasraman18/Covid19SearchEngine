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

class SearchView(APIView):
	def get(self,request):
		api_key = "AIzaSyCPbc8i_1wJhQK5MyuMucgwX4XSsJch2l8"
		resource = build("customsearch", 'v1', developerKey=api_key).cse()
		query = request.GET['query']
		response_json = {}
		fact_check = requests.get('https://factchecktools.googleapis.com/v1alpha1/claims:search',params = {'query':query,'key':api_key})
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
		return Response(response_json)

