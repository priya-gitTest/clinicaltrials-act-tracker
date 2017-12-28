from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from datetime import timedelta

from frontend.models import Sponsor
from frontend.models import Trial


class BasicTestCase(TestCase):

    def setUp(self):
        self.sponsor = Sponsor.objects.create(name="Sponsor 1")
        self.sponsor2 = Sponsor.objects.create(name="Sponsor 2")
        self.due_trial = Trial.objects.create(
            sponsor=self.sponsor,
            registry_id='a1',
            publication_url='http://bar.com/1',
            title='Trial 1',
            start_date=date(2016, 1, 1),
            due_date=date(2016, 2, 1))
        self.reported_trial = Trial.objects.create(
            sponsor=self.sponsor,
            registry_id='a2',
            publication_url='http://bar.com/2',
            title='Trial 2',
            start_date=date(2016, 1, 1),
            due_date=date(2016, 2, 1),
            completion_date=date(2016, 2, 1),
        )
        tomorrow = date.today() + timedelta(days=1)
        self.not_due_trial = Trial.objects.create(
            sponsor=self.sponsor,
            registry_id='a3',
            publication_url='http://bar.com/3',
            title='Trial 3',
            start_date=date(2016, 1, 1),
            due_date=tomorrow
        )

    def test_slug(self):
        self.assertEqual(self.sponsor.slug, 'sponsor-1')

    def test_sponsor_annotation(self):
        self.assertEqual(Sponsor.objects.annotated().first().num_trials, 3)

    def test_sponsor_due(self):
        with_due = Sponsor.objects.with_trials_due()
        self.assertEqual(len(with_due), 1)
        self.assertEqual(with_due.first().num_trials, 2)

    def test_sponsor_unreported(self):
        with_unreported = Sponsor.objects.with_trials_unreported()
        self.assertEqual(len(with_unreported), 1)
        self.assertEqual(with_unreported.first().num_trials, 2)

    def test_sponsor_reported(self):
        with_reported = Sponsor.objects.with_trials_reported()
        self.assertEqual(len(with_reported), 1)
        self.assertEqual(with_reported.first().num_trials, 1)

    def test_sponsor_overdue(self):
        with_overdue = Sponsor.objects.with_trials_overdue()
        self.assertEqual(len(with_overdue), 1)
        self.assertEqual(with_overdue.first().num_trials, 1)

    def test_sponsor_reported_early(self):
        with_reported_early = Sponsor.objects.with_trials_reported_early()
        self.assertEqual(len(with_reported_early), 0)

    def test_trials_due(self):
        self.assertCountEqual(
            self.sponsor.trials.due(),
            [self.due_trial, self.reported_trial])

    def test_trials_unreported(self):
        self.assertCountEqual(
            self.sponsor.trials.unreported(),
            [self.due_trial, self.not_due_trial])

    def test_trials_reported(self):
        self.assertCountEqual(
            self.sponsor.trials.reported(),
            [self.reported_trial])

    def test_trials_overdue(self):
        self.assertCountEqual(
            self.sponsor.trials.overdue(),
            [self.unreported_trial])

    def test_trials_reported_early(self):
        self.assertCountEqual(
            self.sponsor.trials.reported_early(),
            [])