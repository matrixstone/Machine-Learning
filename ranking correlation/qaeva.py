import sys, os, time, glob, json, urllib, math, commands
from xml.dom import minidom
from NDCG import NDCG
import math
import scipy.stats

def doNewsAPI(term):
	newAPI="http://us.proxy.media.search.yahoo.com:4080/xml?age=2d&custid=foo&dups=hide&hits=10&limattributes=shortcutus&limlanguage=en&ranking=usrankmlr&query="
	encodedTerm = urllib.quote_plus(term)
	API=newAPI+encodedTerm
	# print API
	newContent = urllib.urlopen(API).read()
	# print newContent
	newXML = newContent.replace('\n','')
	# print newXML
	# currentTimestamp=os.system("date -u +%s")
	currentTimestamp=int(time.time())
	# print currentTimestamp
	resultsDom = minidom.parseString(newXML)
	totalTime=0
	newsCount=0
	latestTime=10000
	for pubTime in resultsDom.getElementsByTagName('PUBDATE'):
		newsCount+=1
		# print (currentTimestamp-int(pubTime.firstChild.nodeValue))/60/60
		currentNewsTime=(currentTimestamp-int(pubTime.firstChild.nodeValue))/60/60
		totalTime+=currentNewsTime
		if currentNewsTime <= latestTime:
			latestTime=currentNewsTime
	# print "Total news number: %d" % (newsCount)
	if newsCount != 0:
		aveTime=totalTime/newsCount
	else:
		aveTime=0
		print "No News"
		return -1, -1
	# print "Average news time: %d" % (aveTime)
	# print "Latest news time: %d" % (latestTime)
	return latestTime, aveTime


def parseJson(content):
    #parse json to get the terms
    s = json.loads(content)
    li=[]
    # dic={}
    for item in s["candidates"]:
        term=item["searchTerm"]
        # dic[term]=(item["score"]+"\t"+item["categories"][0]
        #            +"\t"+item["searchLink"])
        li.append(term)
    return li

def writeQueries(queries, outputDir):
		try:
			out=open(outputDir+"/LQFinput.txt", 'w')
			for query in queries:
				out.write(query+"\n")
			print >> sys.stderr, "######## Write input queries ########"
		except Exception, em:
			print >> sys.stderr, "Error for PPP write queries. Error Message: %s" % (em)
		out.close()

def readQueries(filename):
		queries=[]
		index=80
		try:
			out=open(filename, 'r')
			lines=out.readlines()
			for line in lines:
				words=line.strip().split("\t")
				queries.append(words[0])
				index-=1
				if index == 0:
					break;
			out.close()
		except Exception, em:
			print >> sys.stderr, "Error for PPP read queries. Error Message: %s" % (em)
		finally:
			return queries
def fetchAPI(url):
	content = urllib.urlopen(url).read()
	queriesList=parseJson(content)
	if len(queriesList) > 80:
		return queriesList[:80]
	else:
		return queriesList

def calNewsLatency(queriesList):
	totalAveTime=0
	totalLatestTime=0
	lenNewJson=len(queriesList)
	for entity in queriesList:
		currentLatestTime, currentAveTime=doNewsAPI(entity)
		if currentLatestTime == -1 and currentAveTime == -1:
			lenNewJson-=1
		else:
			totalAveTime+=currentAveTime
			totalLatestTime+=currentLatestTime
	# print "New Cluster Eva:"
	# print "Average news recency time %d" % (totalAveTime/lenNewJson)
	# print "Average Latest news time %d" % (totalLatestTime/lenNewJson)
	return "%d, %d" % (totalAveTime/lenNewJson, totalLatestTime/lenNewJson)

def main():
	#input 
	(status, timestamp)=commands.getstatusoutput("date +\"%Y-%m-%d-%H-%M\"")
	# print >> sys.stderr, "###### Read input:"
	sourceDir="/home/xuhe/newsLatencyEva/"
	sling="http://us.kvc.search.yahoo.com:4080/kv/get?ns=terms&appid=ttrev&key=sling"
	qaSling="http://qa.kvc.search.yahoo.com:4080/kv/get?ns=terms&appid=ttrev&key=sling_qa"
	# newRankingAPI="http://realapi.timesense.yahoo.com:4080/timesense/v3/en-US-PP-20150223-ALL/topbuzzing?clientid=fpus&format=slingjson&count=600"

	#Do with newRankingAPI
	print >> sys.stderr, "######### Read Sling Key:"
	content = urllib.urlopen(sling).read()
	slingList=parseJson(content)

	print >> sys.stderr, "######### Read QA Sling Key:"
	content = urllib.urlopen(qaSling).read()
	qaslingList=parseJson(content)

	print >> sys.stderr, "######### Overlap between QA and Prod"
	overlapList=list(set(slingList) & set(qaslingList))
	print len(overlapList)
	print "Difference in QA:" 
	print (set(qaslingList) - set(overlapList))
	try:
		output = open("Eva.txt", 'w')
	except Exception, em:
		print >> sys.stderr, "Error in running PPP at %s: %s" % (timestamp, str(em))
		pass
	output.write("#Term\tQA\tProd\tLabel\n")
	countOfSame=0
	for term in overlapList:
		indexOfQA=qaslingList.index(term)
		indexOfSling=slingList.index(term)
		sameRes=1 if indexOfQA == indexOfSling else 0
		if sameRes == 1:
			countOfSame+=1
		output.write("%s\t%s\t%s\t%s\n" % (term, indexOfQA, indexOfSling, sameRes))
	output.close()
	print "Count of same ranking: %d" % countOfSame


	print >> sys.stderr, "######### EVALUATION:"
		#for production
	dcgObj=NDCG()
	try:
		perfectWeight = [1/math.log(1+i) for i in range(1, 81)]
	except Exception, em:
		print i
	# print perfectWeight
	IDCG=dcgObj.DCG(perfectWeight)

	q2weight={}
	for index, query in enumerate(slingList):
		q2weight[query] = perfectWeight[index]

	qaWeightList=[]
	for term in qaslingList:
		qaWeightList.append(q2weight.get(term, 0))
	# print qaWeightList
	DCG=dcgObj.DCG(qaWeightList)
	# print IDCG
	# print DCG
	nDCG = DCG/IDCG
	print >> sys.stderr,  "NDCG:"
	print nDCG
	print "Kendall Tau Correlation"
	tau, p_value = scipy.stats.kendalltau(slingList, qaslingList)
	print tau
	# writeQueries(newRankingList, sourceDir)
	# print >> sys.stderr, "######### Run PPP:"
	# cmd="/home/y/libexec/trendingnow/tn_postpp/run.sh "+sourceDir+"/LQFinput.txt "+sourceDir+"/output.clean.txt"
	# try:
	# 	os.system(cmd)
	# except Exception, em:
	# 	print >> sys.stderr, "Error in running PPP at %s: %s" % (timestamp, str(em))
	# 	pass
	# newRankingList=readQueries(sourceDir+"/output.clean.txt")

	# qaSlingLQFList=fetchAPI(qaSlingLQF)
	# slingList=fetchAPI(sling)

	# # Average news recency time, Average Latest news time
	# print >> sys.stderr, "######### Calculate recency:"
	# newRankingResult=calNewsLatency(newRankingList)
	# qaSlingLQFResult=calNewsLatency(qaSlingLQFList)
	# slingResult=calNewsLatency(slingList)

	# result="%s\t%s\t%s\t%s" % (timestamp, slingResult, newRankingResult, qaSlingLQFResult)
	# cmd="echo \"%s\" >> %s/latencyResult.txt" % (result, sourceDir) 
	# os.system(cmd)

if __name__ == '__main__':
	main()