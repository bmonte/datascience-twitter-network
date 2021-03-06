import logging
import pandas as pd
from queue import Queue
from threading import Thread
from tweepy import StreamListener
from src.setup import settings

# Logger

# Get Logger instance
__logger__ = logging.getLogger()

class TweetListener(StreamListener) :

	""" This class retrieves tweeets that match certain criteria  """

	def __init__(self, api):
		self.api = api
		self.me = api.me()
		self.tweet_queue = Queue() # Store tweets from tweepy stream
		self.tweet_list = [] # Store processed tweets

		# Create 5 threads to filter tweets
		for i in range(5) :

			filter_tweet_thread = Thread(target = self.filter)
			filter_tweet_thread.daemon = True
			filter_tweet_thread.start()


	def on_status(self, tweet):

		""" Tweepy.StreamListener.on_status override """

		if len(self.tweet_list) < settings.threshold : # Stream threshold

			# Add tweet to the queue
			self.tweet_queue.put(tweet)

		else :

			__logger__.info('Stream threshold reached.')

			self.persist()

			return False
		

	def filter(self) :

		""" Filter tweets from Tweepy stream """

		while True :

			# Get a tweet from streaming queue
			tweet = self.tweet_queue.get()

			if hasattr(tweet, 'retweeted_status') : # Keep only RTs

				# Tweets text can be truncated. The full text is required anyway
				text = tweet.extended_tweet['full_text'] if hasattr(tweet, 'extended_tweet') else tweet.text

				t = [
					tweet.id,
					str(tweet.created_at),
					tweet.user.location if tweet.user.location else '',
					text,
					tweet.retweeted_status.user.screen_name,
					tweet.user.screen_name,
					' '.join([hashtag.get('text') for hashtag in tweet.entities['hashtags']]),
					' '.join([user_mention.get('screen_name') for user_mention in tweet.entities['user_mentions']])
				]

				# Show tweet info
				print(len(self.tweet_list), t)

				# Store processed tweet
				self.tweet_list.append(t)


			self.tweet_queue.task_done()


	def persist(self) :

		""" Persist tweets data """		

		__logger__.info(f'Persisting {len(self.tweet_list)} tweets...')

		tweets_df = pd.DataFrame(self.tweet_list, columns = ['id', 'datetime', 'user_location', 'text', 'from', 'by', 'hashtags', 'mentions'])

		storage = f'data/tweets_{settings.running_at}.csv'

		tweets_df.to_csv(storage, index = False)

		__logger__.info(f'Tweets saved at {storage}')


	def on_exception(self, exception) :

		""" Exception handling """

		__logger__.exception(exception)

		self.persist()

		raise exception
