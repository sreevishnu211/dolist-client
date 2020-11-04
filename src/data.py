'''
MIT License

Copyright (c) 2020 Cedric Fauth

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import re
import logging
from cli import Output as O
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Dataparser():

	days_to_int = {"mon" : 0, "tue" : 1, "wed" : 2, "thu" : 3,
		"fri" : 4, "sat" : 5, "sun" : 6 }

	@staticmethod
	def validate(args):
		'''
		validates input values of the user
		'''
		# only need to validate if cmd is event or task
		if args.cmd == 'event' or args.cmd == 'task':
			# -t -d -f are available but -d is optional

			# try to match -f w/o/d
			if not re.match('^(w|weekly|d|daily|o|once)$', args.f):
				O.error(f'wrong frequency format: {args.f}')
				return False
			
			# if daily: no date/day set
			if args.f[0] == 'd':
				if args.d != None:
					O.error(f'you cannot use -d here because the {args.cmd} is daily.')
					return False
			# if once: date YYYY-MM-DD needs to be set
			elif args.f[0] == 'o':
				if not args.d or not re.match('^((\d\d\d\d)-(0[1-9]|1[0-2])-(0[1-9]|(1|2)[0-9]|3[0-1]))$', args.d):
					O.error(f'wrong date format: {args.d}')
					return False
			# if weekly: day needs to be set
			else:
				if not args.d or not re.match('^(mon|tue|wed|thur|fri|sat|sun)$', args.d):
					O.error(f'wrong day format: {args.d}')
					return False
			
			# if event try to match HH:MM-HH:MM
			if args.cmd == 'event':
				if not re.match('^([0-1][0-9]|2[0-3]):[0-5][0-9]-([0-1][0-9]|2[0-3]):[0-5][0-9]$', args.t):
					O.error(f'wrong time format: {args.t}')
					return False
			# if event try to match HH:MM
			else:
				if not re.match('^([0-1][0-9]|2[0-3]):[0-5][0-9]$', args.t):
					O.error(f'wrong time format: {args.t}')
					return False
		return True

	@staticmethod
	def parse(c, title, day_date, time, freq):
		'''
		weekly event data gets prepared for database
		'''

		f = freq[0]
		day = None
		date = None
		if f == 'o':
			date = day_date
		elif f == 'w':
			day = Dataparser.days_to_int[day_date]
		
		if c =='e':
			t = time.split('-')
			return (title, day ,t[0], t[1], f, date)
		else:
			return (title, day, time, f, date)
	
	@staticmethod
	def nearest_deadline(task):
		freq = task[4]
		# date now
		dt = datetime.now()
		date_str = dt.date().isoformat()
		# time now
		current_time_str = dt.strftime("%H:%M")
		current_datetime = datetime.fromisoformat(f'{date_str} {current_time_str}')
		deadline_datetime = datetime.fromisoformat(f'{date_str} {task[3]}')
		
		print(current_time_str)
		print(current_datetime)
		print(deadline_datetime)

		if freq == 'w':
			while 1:
				if deadline_datetime.weekday() == task[2]:
					if deadline_datetime > current_datetime:
						break
				deadline_datetime += timedelta(1)
			if task[7]:
				last_done = datetime.fromisoformat(task[7])
				if deadline_datetime - last_done > timedelta(7):
					deadline_datetime -= timedelta(1)
		elif freq == 'd':
			if deadline_datetime <= current_datetime:
				deadline_datetime += timedelta(1)
			if task[7]:
				last_done = datetime.fromisoformat(task[7])
				if deadline_datetime - last_done > timedelta(1):
					print(deadline_datetime - last_done)
					deadline_datetime -= timedelta(1)
		else:
			deadline_datetime = datetime.fromisoformat(f'{task[5]} {task[3]}')

		print(deadline_datetime)

		return deadline_datetime
	
	@staticmethod
	def date_of_last_weekday(weekday):
		day = date.today()
		while day.weekday() != weekday:
			day -= timedelta(1)
		return day

	@staticmethod
	def delta_to_tupel(tdelta):
		hours, rem = divmod(tdelta.seconds, 3600)
		minutes = rem // 60 # + 1
		return (tdelta.days, hours, minutes, )

	@staticmethod
	def prepare_out_events(events):
		"""
		creates list of events with additional attibs like 'time left'
		"""
		event_list = []
		daytime = datetime.today()
		day = date.today()
		for e in events:
			task_time = datetime.fromisoformat(f'{day.isoformat()} {e[3]}')
			left = task_time - daytime
			#print(f'{e[1]} : {Dataparser.delta_to_tupel(left)}')
			event_list.append(e + Dataparser.delta_to_tupel(left))
		return event_list
		

	@staticmethod
	def prepare_out_tasks(tasks):
		"""
		creates list of tasks with additional attibs like 'time left'
		"""
		task_list = []
		daytime = datetime.today()
		day = date.today()
		for t in tasks:
			left = None
			# info: stays missed until new day begins
			
			deadline_datetime = Dataparser.nearest_deadline(t)
			logger.debug(deadline_datetime)
			left = deadline_datetime - daytime

			task_list.append(t + Dataparser.delta_to_tupel(left))

		def time_left_to_str(x):
			#if x[8] < 0:
			#	y = int(f'{x[8]}{((x[9]*(-1) + 24) % 24):02}{x[10]:02}')
			#else:
			y = int(f'{x[8]}{x[9]:02}{x[10]:02}')
			return y

		return sorted(task_list, key=time_left_to_str)

	@staticmethod
	def get_reset_ids(tasks_done):
		# TODO maybe wrong because of many changes
		task_ids = []
		daytime = datetime.today()
		day = date.today()
		for t in tasks_done:
			left = None
			if t[4] != 'o':
				task_time = datetime.fromisoformat(f'{day.isoformat()} {t[3]}')
				left = task_time - daytime
				if left.days < 0:
					# check if last-done is before last due: reset
					if datetime.fromisoformat(t[7]) == task_time:
						logger.info(f'{t[1]} can be deleted')
						task_ids.append(t[0])
		return task_ids

		# TODO task for next week/day cannot be done on last due day
