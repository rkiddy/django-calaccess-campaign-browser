from optparse import make_option
from django.db import connection
from django.db.models import get_model
from django.db.utils import OperationalError
from django.core.management.base import LabelCommand
from calaccess_campaign_browser.management.commands import CalAccessCommand

from _mysql_exceptions import Warning

import sys


class Command(CalAccessCommand):

    def executeSqls(self, isDryRun, sqls):
        for sql in sqls:
            if isDryRun:
                print sql
            else:
                c = connection.cursor()
                try:
                    c.execute(sql)
                except Exception:
                    pass
                c.close()


    help = "Split CAL-ACCESS filings by year"

    option_list = LabelCommand.option_list + (
        make_option(
            '-N',
            dest="dry_run_all",
            action="store_true",
            default=False,
            help="Execute a dry run; do not execute any of the SQL, including for FILER_FILINGS"
        ),
        make_option(
            '-n',
            dest="dry_run",
            action="store_true",
            default=False,
            help="Execute a dry run; do not execute any of the SQL, except for FILER_FILINGS."
        ),
        make_option(
            '--verbose', '-v',
            dest="verbose",
            action="store_true",
            default=False,
            help="Verbose output."
        ),
    )

    def handle(self, *args, **options):
        self.header("Splitting filings")

        dryRunAll = options['dry_run_all']
        dryRun = options['dry_run']
        verbose = options['verbose']

        if verbose:
            print "dryRunAll is %s" % dryRunAll
            print "dryRun is %s" % dryRun

        tables = [
            'CvrCampaignDisclosureCd',
            'CvrE530Cd',
            'CvrLobbyDisclosureCd',
            'CvrRegistrationCd',
            'CvrSoCd',
            'Cvr2CampaignDisclosureCd',
            'Cvr2LobbyDisclosureCd',
            'Cvr2RegistrationCd',
            'Cvr2SoCd',
            'Cvr3VerificationInfoCd',
            'DebtCd',
            'ExpnCd',
            'F495P2Cd',
            'F501502Cd',
            'F690P2Cd',
            'FilingsCd',
            'HdrCd',
            'LattCd',
            'LccmCd',
            'LempCd',
            'LexpCd',
            'LoanCd',
            'LobbyistFirmEmployer1Cd',
            'LobbyistFirmEmployer2Cd',
            'LobbyAmendmentsCd',
            'LothCd',
            'LpayCd',
            'RcptCd',
            'ReceivedFilingsCd',
            'S401Cd',
            'S496Cd',
            'S497Cd',
            'S498Cd',
            'SmryCd',
            'SpltCd',
            'TextMemoCd'
        ]

        # tables = ['LpayCd', 'SmryCd']

        years = []

        for year in range(2000, 2016):
            years.append(str(year))

        # years = ['2014', '2015']

        if not dryRun:

            for year in years:

                self.success('  table: FILER_FILINGS_CD year: %s' % year)

                sqls = []

                # First, split the filer_filings table
                #
                sqls.append("""
                    drop table if exists FILER_FILINGS_CD_%s
                """ % year)

                sqls.append("""
                    create table FILER_FILINGS_CD_%s like FILER_FILINGS_CD
                """ % year)

                sqls.append("""
                    insert into FILER_FILINGS_CD_%s select * from FILER_FILINGS_CD
                    where RPT_END >= '%s-01-01' and RPT_END <= '%s-12-31'
                """ % (year, year, year))

                self.executeSqls(dryRunAll, sqls)

            self.success('  table: FILER_FILINGS_CD year: else')

            sqls = []

            sqls.append("""
                drop table if exists FILER_FILINGS_CD_else
            """)

            sqls.append("""
                create table FILER_FILINGS_CD_else like FILER_FILINGS_CD
            """)

            sqls.append("""
                insert into FILER_FILINGS_CD_else select * from FILER_FILINGS_CD
                where RPT_END <= '2000-01-01' or RPT_END >= '2015-12-31'
            """)

            self.executeSqls(dryRunAll, sqls)

        if dryRunAll:
            exit()

        for year in years:

            sql = """
                select FILING_ID from FILER_FILINGS_CD_%s
            """ % year

            filingIds = []

            c = connection.cursor()

            c.execute(sql)

            for row in c.fetchall():
                filingIds.append(str(row[0]))

            c.close()

            for table in tables:

                sqls = []

                tableName = str(get_model('calaccess_raw', table)._meta.db_table)

                self.success('  table: %s year: %s' % (tableName, year))

                sqls.append("""
                    drop table if exists %s_%s
                """ % (tableName, year))

                sqls.append("""
                    create table %s_%s like %s
                """ % (tableName, year, tableName))

                sqls.append("""
                    insert into %s_%s select * from %s where FILING_ID in (%s)
                """ % (tableName, year, tableName, ','.join(filingIds)))

                self.executeSqls(dryRun, sqls)
