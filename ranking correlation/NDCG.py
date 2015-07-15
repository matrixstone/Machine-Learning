import math
class NDCG():

	def DCG(self, weightList):
		dcg = 0.0 + weightList[0]
		for index, weight in enumerate(weightList):
			denominator = math.log(index+1,2)
			if not denominator == 0.0:
				dcg += (math.pow(2, weight)-1)/denominator
		return dcg

	# def NDCG(self, count):
	# 	perfectWeight = [i for i in range(count, 0, -1)]
	# 	IDCG=DCG(perfectWeight)

if __name__ == '__main__':
	main()