# -*- coding: utf-8 -*-
"""
Created on Sun Jul 16 17:29:33 2017

@author: ANalluri
@update: Sanders
"""

import math
from utils import get_char_count
from utils import get_words
from utils import get_sentences
from utils import count_syllables
from utils import count_complex_words
import time
import re
import mysql.connector
from mysql.connector import errorcode
from textstat.textstat import textstat

import sqlite3
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import nltk
import codecs
import urllib2
ddir = '.'

class Readability:
    analyzedVars = {}

    def __init__(self, text):
        self.analyze_text(text)

    def analyze_text(self, text):
        words = get_words(text)
        char_count = get_char_count(words)
        word_count = len(words)
        sentence_count = len(get_sentences(text))
        syllable_count = count_syllables(words)
        complexwords_count = count_complex_words(text)
        avg_words_p_sentence = word_count/sentence_count

        self.analyzedVars = {
            'words': words,
            'char_cnt': float(char_count),
            'word_cnt': float(word_count),
            'sentence_cnt': float(sentence_count),
            'syllable_cnt': float(syllable_count),
            'complex_word_cnt': float(complexwords_count),
            'avg_words_p_sentence': float(avg_words_p_sentence)
        }

    def ARI(self):
        score = 0.0
        if self.analyzedVars['word_cnt'] > 0.0:
            score = 4.71 * (self.analyzedVars['char_cnt'] / self.analyzedVars['word_cnt']) + 0.5 * (self.analyzedVars['word_cnt'] / self.analyzedVars['sentence_cnt']) - 21.43
        return score

    def FleschReadingEase(self):
        score = 0.0
        if self.analyzedVars['word_cnt'] > 0.0:
            score = 206.835 - (1.015 * (self.analyzedVars['avg_words_p_sentence'])) - (84.6 * (self.analyzedVars['syllable_cnt']/ self.analyzedVars['word_cnt']))
        return round(score, 4)

    def FleschKincaidGradeLevel(self):
        score = 0.0
        if self.analyzedVars['word_cnt'] > 0.0:
            score = 0.39 * (self.analyzedVars['avg_words_p_sentence']) + 11.8 * (self.analyzedVars['syllable_cnt']/ self.analyzedVars['word_cnt']) - 15.59
        return round(score, 2)

    def GunningFogIndex(self):
        score = 0.0
        if self.analyzedVars['word_cnt'] > 0.0:
            score = 0.4 * ((self.analyzedVars['avg_words_p_sentence']) + (100 * (self.analyzedVars['complex_word_cnt']/self.analyzedVars['word_cnt'])))
        return round(score, 2)

    def SMOGIndex(self):
        score = 0.0
        if self.analyzedVars['word_cnt'] > 0.0:

            score = 1.0430*(math.sqrt((self.analyzedVars['complex_word_cnt']*30)/self.analyzedVars['sentence_cnt'])) + 3.1291
        return round(score,2)

def ParseXML():
	data = []
	groups = []
	print 'READ XML FILE'
	#file="mplus_topics_2017-10-28.xml"
	html_page = urllib2.urlopen("https://medlineplus.gov/xml.html")
	soup = BeautifulSoup(html_page)
	parse_file=""
	for link in soup.findAll('a', attrs={'href': re.compile("^https://medlineplus.gov/xml/mplus_topics_")}):
		file=link.get('href')
		if (".xml" in file):
			parse_file=urllib2.urlopen(file)
			print file
			break  ### find the first file

	tree = ET.parse(parse_file)
	root = tree.getroot()
	### loop through each topic
	for child in root:
		### get only English ariticles
		if child.attrib['language']=='English':
			### get article url, id, and title
			### get article details, e.g. full summary and groups
			### save the summary text to a file
			tid = child.attrib['id']
			title = child.attrib['title']
			url = child.attrib['url']
			summaryHtml = ''
			summaryText = ''
			for grandchild in child:
				if grandchild.tag=='full-summary':
					summaryHtml = grandchild.text
					#print summaryHtml.encode('utf-8').strip()
					### get text
					soup = BeautifulSoup(summaryHtml, 'html.parser')
					summaryText = soup.get_text()
					sents = []
					for sent in summaryText.split('\n'):
						if sent=='':
							pass
						else:
					 		sents += nltk.tokenize.sent_tokenize(sent)
					#print sents
					### export topic text in sentences, ASCII only
					finput = './01_topics/%04d.txt' % int(tid)
					with codecs.open(finput,'w',encoding='ascii',errors='ignore') as f:
						for i in range(0,len(sents)):
							f.write(sents[i].strip() + '\n')
					### create also an empty annotation file
					with open(finput.replace('.txt','.ann'),'w') as f:
						f.write('')
				if grandchild.tag=='group':
					topic_id=child.attrib['id']
					group_id=grandchild.attrib['id']
					group_name=grandchild.text.encode('utf-8').strip()
					groups.append([child.attrib['id'],grandchild.attrib['id'],grandchild.text.encode('utf-8').strip()])
					add_group = ("INSERT INTO topic_group "
					" (topic_id,group_id,group_name) "
					"VALUES (%s,%s, %s)")
					data_group = (str(topic_id),str(group_id), str(group_name))
					cursor3.execute(add_group, data_group)
					cnx3.commit()
			dtTmp = child.attrib['date-created']
			dt = "%s-%s-%s" % (dtTmp[6:],dtTmp[0:2],dtTmp[3:5])
			row = [tid,title,dt,url,summaryHtml,summaryText]
			data.append(row)
			add_topic = ("INSERT INTO src_mlp "
                " (topic_id,title,date_created,url,summary_html,summary_text) "
                "VALUES (%s,%s, %s, %s, %s,%s)")
  			data_topic = (str(tid),str(title.encode('utf-8')), str(dt),str(url),str(summaryHtml.encode('utf-8')),str(summaryText.encode('utf-8')) )
			cursor3.execute(add_topic, data_topic)
			cnx3.commit()
			#break
	print 'READ %s topics and %s groups' % (len(data),len(groups))
	#return data, groups

def scores_cal(text):
     rd = Readability(text)
     char_count_value=rd.analyzedVars['char_cnt']
     lexicon_count_value=rd.analyzedVars['word_cnt']
     syllable_count_value=rd.analyzedVars['syllable_cnt']
     sentence_count_value=rd.analyzedVars['sentence_cnt']
     avg_sentence_length_value=rd.analyzedVars['word_cnt']/rd.analyzedVars['sentence_cnt']
     avg_syllables_per_word_value=rd.analyzedVars['syllable_cnt']/rd.analyzedVars['word_cnt']
     avg_letter_per_word_value=rd.analyzedVars['char_cnt']/rd.analyzedVars['word_cnt']
     avg_sentence_per_word_value=rd.analyzedVars['sentence_cnt']/rd.analyzedVars['word_cnt']
     flesch_kincaid_grade_value=rd.FleschKincaidGradeLevel()
     smog_index_value=rd.SMOGIndex()
     gunning_fog_value=rd.GunningFogIndex()
     difficult_words_value=rd.analyzedVars['complex_word_cnt']
     dale_chall_value=0
     return char_count_value,lexicon_count_value,syllable_count_value,sentence_count_value,avg_sentence_length_value,avg_syllables_per_word_value,avg_letter_per_word_value,avg_sentence_per_word_value,flesch_kincaid_grade_value,smog_index_value,gunning_fog_value,difficult_words_value,dale_chall_value


def scores_cal_ori(text):

              char_count_value=textstat.char_count(text,ignore_spaces=True)
              lexicon_count_value=textstat.lexicon_count(text,removepunct=True)
              syllable_count_value=textstat.syllable_count(text)
              sentence_count_value=textstat.sentence_count(text)
              avg_sentence_length_value=textstat.avg_sentence_length(text)
              avg_syllables_per_word_value=textstat.avg_syllables_per_word(text)
              avg_letter_per_word_value=textstat.avg_letter_per_word(text)
              avg_sentence_per_word_value=textstat.avg_sentence_per_word(text)
              flesch_kincaid_grade_value=textstat.flesch_kincaid_grade(text)
              smog_index_value=textstat.smog_index(text)
              gunning_fog_value=textstat.gunning_fog(text)
              difficult_words_value=textstat.difficult_words(text)
              dale_chall_value=textstat.dale_chall_readability_score(text)
              polysyllab_value=textstat.polysyllabcount(text)
              return char_count_value,lexicon_count_value,syllable_count_value,sentence_count_value,avg_sentence_length_value,avg_syllables_per_word_value,avg_letter_per_word_value,avg_sentence_per_word_value,flesch_kincaid_grade_value,smog_index_value,gunning_fog_value,difficult_words_value,dale_chall_value,polysyllab_value
              return smog_index_value
#cursor1
db_connection1=0
records_count1=0

try:
 cnx1 = mysql.connector.connect(user='Aishwarya', password='nalluraa2017',
                              host='10.23.20.230',
                              database='pubmed')
 cursor1=cnx1.cursor(buffered=True)

except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
      print("Something is wrong with your user name or password in cursor 1")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
      print("Database does not exist- cursor 1")
  else:
      print(err)
else:
    db_connection1=1

#cursor 2
db_connection2=0
records_count2=0

try:
 cnx2 = mysql.connector.connect(user='Aishwarya', password='nalluraa2017',
                              host='10.23.20.230',
                              database='pubmed')
 cursor2=cnx2.cursor(buffered=True)

except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
   print("Something is wrong with your user name or password in cursor2")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
   print("Database does not exist - cursor2")
  else:
   print(err)
else:
 db_connection2=1

#cursor3
db_connection3=0
try:
 cnx3 = mysql.connector.connect(user='Aishwarya', password='nalluraa2017',
                              host='10.23.20.230',
                              database='pubmed')
 cursor3=cnx3.cursor(buffered=True)

except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
      print("Something is wrong with your user name or password in cursor 3")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
      print("Database does not exist- cursor 3")
  else:
      print(err)
else:
    db_connection3=1

if db_connection1==1 and db_connection2==1 and db_connection3==1:
     sql1="SELECT * FROM src_mlp"
     sql2=("INSERT INTO scores_mlp"
           "(ID,Data_type,char_count,lexicon_count,syllable_count,sentence_count,avg_sentence_length,avg_syllables_per_word,avg_letter_per_word,avg_sentence_per_word,flesch_kincaid_grade,smog_index,gunning_fog,difficult_words,dale_chall)"
           "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")

	 ###clean all existing records and get latest xml file
     sql3="""TRUNCATE TABLE src_mlp"""
     cursor3.execute(sql3)

     sql3="""TRUNCATE TABLE scores_mlp"""
     cursor3.execute(sql3)
     sql3="""TRUNCATE TABLE topic_group"""
     cursor3.execute(sql3)
     cnx3.commit()
     ParseXML()

	 ### Start calculating scores
     cursor1.execute(sql1)
     results=cursor1.fetchall()
     for row in results:
        topic_id_value=row[0]
        title_value=row[1]
        summary_text_value=row[5]

        tu=scores_cal(summary_text_value)
        s_index=0
        s_index=scores_cal(summary_text_value)
        print(s_index)
        time.sleep(1)
        print("==============================")

        data_final=(topic_id_value,'text',tu[0],tu[1],tu[2],tu[3],tu[4],tu[5],tu[6],tu[7],tu[8],tu[9],tu[10],tu[11],tu[12])
        cursor2.execute(sql2,data_final)
        records_count2=records_count2+1

     print("Records inserted:"+ str(records_count2))
     cnx2.commit()
     cursor1.close()
     cursor2.close()
     cursor3.close()
     cnx1.close()
     cnx2.close()
     cnx3.close()
