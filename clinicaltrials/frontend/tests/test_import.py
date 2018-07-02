from datetime import date
from unittest import mock
import os

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from frontend.models import Ranking
from frontend.models import Trial

from frontend.trial_computer import qa_start_date
from frontend.management.commands.process_data import EARLIEST_CANCELLATION_DATE


class DummyResponse(object):
    def __init__(self, content):
        self.content = content
        self.text = str(content)


def mock_ccgov_results(fixture_id):
    fixture_path = os.path.join(
        settings.BASE_DIR,
        'frontend/tests/fixtures/{}.html'.format(fixture_id))
    if os.path.exists(fixture_path):
        with open(fixture_path, 'r') as dummy_response:
            return DummyResponse(dummy_response.read())
    return DummyResponse('<html></html>')



def ccgov_results_by_url(url):
    fixture_id = url.split('/')[-1]
    return mock_ccgov_results(fixture_id)


class CommandsTestCase(TestCase):
    @mock.patch('requests.get', mock.Mock(side_effect=ccgov_results_by_url))
    @mock.patch('frontend.trial_computer.date')
    def test_import(self, datetime_mock):
        "Does a simple import create expected rankings and sponsors?"
        datetime_mock.today = mock.Mock(return_value=date(2018,1,1))

        args = []
        sample_csv = os.path.join(settings.BASE_DIR, 'frontend/tests/fixtures/sample_bq.csv')
        opts = {'input_csv': sample_csv}
        call_command('process_data', *args, **opts)

        reported = Trial.objects.get(registry_id='reported')
        self.assertEqual(reported.status, 'reported')
        self.assertEqual(reported.days_late, None)

        ongoing = Trial.objects.get(registry_id='ongoing')
        self.assertEqual(ongoing.status, 'ongoing')
        self.assertEqual(ongoing.days_late, None)

        overdue = Trial.objects.get(registry_id='overdue')
        self.assertEqual(overdue.status, 'overdue')
        self.assertEqual(overdue.days_late, 61)

        overdueinqa = Trial.objects.get(registry_id='overdueinqa')
        self.assertEqual(overdueinqa.status, 'reported-late')
        self.assertEqual(overdueinqa.days_late, 12)
        self.assertEqual(qa_start_date(overdueinqa), date(2017,11,13))

        late_sponsor_ranking = Ranking.objects.filter(sponsor=overdueinqa.sponsor).first()
        self.assertEqual(late_sponsor_ranking.days_late, 73)
        self.assertEqual(late_sponsor_ranking.finable_days_late, 31)

        self.assertEqual(Ranking.objects.first().days_late, None)
        self.assertEqual(Ranking.objects.first().finable_days_late, None)

        overdueingrace = Trial.objects.get(registry_id='overdueingrace')
        self.assertEqual(overdueingrace.status, 'ongoing')
        self.assertEqual(overdueingrace.days_late, None)

        self.assertEqual(Ranking.objects.first().sponsor, reported.sponsor)
        self.assertEqual(Ranking.objects.count(), 3)


    @mock.patch('requests.get', mock.Mock(side_effect=ccgov_results_by_url))
    @mock.patch('frontend.trial_computer.date')
    @mock.patch('frontend.management.commands.process_data.date')
    def test_second_import(self, mock_date_1, mock_date_2):
        """Does importing the same data twice on subsequent days affect
        individual trials as expected?
        """
        mock_date_1.today = mock.Mock(return_value=date(2018,1,1))
        mock_date_2.today = mock.Mock(return_value=date(2018,1,1))

        args = []
        sample_csv = os.path.join(settings.BASE_DIR, 'frontend/tests/fixtures/sample_bq.csv')
        opts = {'input_csv': sample_csv}
        call_command('process_data', *args, **opts)

        overdue = Trial.objects.get(registry_id='overdue')
        self.assertEqual(overdue.status, 'overdue')
        self.assertEqual(overdue.days_late, 61)
        # Pretend the previous import took place ages ago
        Trial.objects.all().update(updated_date=date(2017,1,1))

        # Import again
        mock_date_1.today = mock.Mock(return_value=date(2018,1,2))
        mock_date_2.today = mock.Mock(return_value=date(2018,1,2))
        call_command('process_data', *args, **opts)

        overdue = Trial.objects.get(registry_id='overdue')
        self.assertEqual(overdue.status, 'overdue')
        self.assertEqual(overdue.days_late, 62)

        self.assertEqual(overdue.updated_date, date(2018,1,2))
        self.assertEqual(overdue.first_seen_date, date(2018,1,1))

    @mock.patch('requests.get', mock.Mock(side_effect=ccgov_results_by_url))
    @mock.patch('frontend.models.date')
    def test_second_import_with_disappeared_trials(self, datetime_mock):
        """Is the disappearance of a trial from the CSV reflected in our
        database?"""
        datetime_mock.today = mock.Mock(return_value=date(2018, 1, 1))

        sample_csv = os.path.join(settings.BASE_DIR, 'frontend/tests/fixtures/sample_bq.csv')
        opts = {'input_csv': sample_csv}
        call_command('process_data', **opts)

        # Pretend the previous import took place ages ago
        date_in_the_past = date(2017, 1, 1)
        Trial.objects.all().update(updated_date=date_in_the_past)

        # Import empty file
        sample_csv = os.path.join(settings.BASE_DIR, 'frontend/tests/fixtures/sample_bq_empty.csv')
        opts = {'input_csv': sample_csv}
        call_command('process_data', **opts)

        # There should be no Trials visible
        self.assertEqual(Trial.objects.count(), 6)
        self.assertEqual(Trial.objects.visible().count(), 0)
        self.assertNotEqual(Trial.objects.first().updated_date, date_in_the_past)


    @mock.patch('requests.get', mock.Mock(side_effect=ccgov_results_by_url))
    @mock.patch('frontend.trial_computer.date')
    def test_qa(self, datetime_mock):
        "Does a simple import create expected rankings and sponsors?"
        datetime_mock.today = mock.Mock(return_value=date(2018,1,1))

        args = []
        sample_csv = os.path.join(settings.BASE_DIR, 'frontend/tests/fixtures/sample_bq_qa.csv')
        opts = {'input_csv': sample_csv}
        call_command('process_data', *args, **opts)

        overdueinqa = Trial.objects.get(registry_id='overdueinqa')
        qa = overdueinqa.trialqa_set.all()
        self.assertEqual(len(qa), 3)
        self.assertEqual(qa[0].returned_to_sponsor, date(2017, 12, 11))
        self.assertEqual(qa[2].returned_to_sponsor, None)

        overdueinqa_cancelled = Trial.objects.get(registry_id='overdueinqa_cancelled')
        qa = overdueinqa_cancelled.trialqa_set.all()
        self.assertEqual(len(qa), 1)
        self.assertEqual(qa[0].submitted_to_regulator, date(2017, 10, 19))
        self.assertEqual(qa[0].cancelled_by_sponsor, EARLIEST_CANCELLATION_DATE)
        self.assertEqual(qa[0].cancellation_date_inferred, True)
        self.assertEqual(qa[0].returned_to_sponsor, None)

        overdueinqa_uncancelled = Trial.objects.get(registry_id='overdueinqa_uncancelled')
        qa = overdueinqa_uncancelled.trialqa_set.all()
        self.assertEqual(len(qa), 2)

        self.assertEqual(qa[0].submitted_to_regulator, date(2018, 3, 29))
        self.assertEqual(qa[0].cancelled_by_sponsor, EARLIEST_CANCELLATION_DATE)
        self.assertEqual(qa[0].cancellation_date_inferred, True)
        self.assertEqual(qa[0].returned_to_sponsor, None)
        self.assertEqual(qa[1].submitted_to_regulator, date(2018, 5, 10))
        self.assertEqual(qa[1].cancelled_by_sponsor, None)
        self.assertEqual(qa[1].returned_to_sponsor, None)

        overdueinqa_cancelled_with_dates = Trial.objects.get(
            registry_id='overdueinqa_cancelled_with_dates')
        qa = overdueinqa_cancelled_with_dates.trialqa_set.all()
        self.assertEqual(len(qa), 2)
        self.assertEqual(qa[0].submitted_to_regulator, date(2018, 5, 4))
        self.assertEqual(qa[0].cancelled_by_sponsor, date(2018, 5, 15))
        self.assertEqual(qa[0].cancellation_date_inferred, False)
        self.assertEqual(qa[1].submitted_to_regulator, date(2018, 5, 15))
        self.assertEqual(qa[1].cancelled_by_sponsor, date(2018, 5, 16))
        self.assertEqual(qa[1].cancellation_date_inferred, False)

        qa = Trial.objects.get(
            registry_id='overdueinqa_manycancelled').trialqa_set.all()
        self.assertEqual(len(qa), 5)
        self.assertEqual(qa[0].submitted_to_regulator, date(2017, 9, 25))
        self.assertEqual(qa[0].cancelled_by_sponsor, EARLIEST_CANCELLATION_DATE)
        self.assertEqual(qa[0].cancellation_date_inferred, True)
        self.assertEqual(qa[3].submitted_to_regulator, date(2018, 4, 12))
        self.assertEqual(qa[3].cancelled_by_sponsor, date(2018, 5, 14))
        self.assertEqual(qa[3].cancellation_date_inferred, False)
        self.assertEqual(qa[4].submitted_to_regulator, date(2018, 5, 14))
        self.assertEqual(qa[4].cancelled_by_sponsor, None)

        qa = Trial.objects.get(
            registry_id='overdueinqa_cancelled_after_returned').trialqa_set.all()
        self.assertEqual(len(qa), 3)
        self.assertEqual(qa[0].submitted_to_regulator, date(2017, 4, 25))
        self.assertEqual(qa[0].cancelled_by_sponsor, None)
        self.assertEqual(qa[0].returned_to_sponsor, date(2017, 8, 8))
        self.assertEqual(qa[1].submitted_to_regulator, date(2017, 10, 2))
        self.assertEqual(qa[1].cancelled_by_sponsor, date(2018, 5, 17))
        self.assertEqual(qa[2].submitted_to_regulator, date(2018, 5, 17))


    @mock.patch('requests.get')
    @mock.patch('frontend.trial_computer.date')
    def test_import_twice(self, datetime_mock, requests_mock):
        "Is importing idempotent?"
        datetime_mock.today = mock.Mock(return_value=date(2018,1,1))
        args = []
        sample_csv = os.path.join(settings.BASE_DIR, 'frontend/tests/fixtures/two_months_qa.csv')
        opts = {'input_csv': sample_csv}

        def month_1_results(arg):
            return mock_ccgov_results('overdueinqa_month_1')
        requests_mock.side_effect = month_1_results
        call_command('process_data', *args, **opts)

        def month_2_results(arg):
            return mock_ccgov_results('overdueinqa_month_2')
        requests_mock.side_effect = month_2_results
        call_command('process_data', *args, **opts)

        qa = Trial.objects.get(
            registry_id='overdueinqa_two_months').trialqa_set.all()
        self.assertEqual(len(qa), 1)
        self.assertEqual(qa[0].submitted_to_regulator, date(2017, 11, 13))
        self.assertEqual(qa[0].returned_to_sponsor, date(2017, 12, 11))
