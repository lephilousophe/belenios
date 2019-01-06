#!/usr/bin/python
# -*- coding: utf-8 -*
import unittest
import time
import string
import random
import os
import shutil
import subprocess
import re
import sys
from distutils.util import strtobool
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
from util.fake_sent_emails_manager import FakeSentEmailsManager
from util.selenium_tools import wait_for_element_exists, wait_for_elements_exist, wait_for_element_exists_and_contains_expected_text, wait_for_element_exists_and_has_non_empty_content, wait_for_an_element_with_partial_link_text_exists
from test_scenario_1 import console_log, remove_database_folder, initialize_server, initialize_browser, log_in_as_administrator, log_out, wait_a_bit, verify_element_label, random_email_addresses_generator, administrator_starts_creation_of_election, administrator_edits_election_questions, administrator_sets_election_voters, build_css_selector_to_find_buttons_in_page_content_by_value
import settings


def initialize_browser_for_scenario_2():
    return initialize_browser(for_scenario_2=True)


class BeleniosTestElectionScenario2(unittest.TestCase):
    """
    Properties:
    - server
    - browser
    - voters_email_addresses
    - voters_email_addresses_who_have_lost_their_password
    - voters_data
    - election_page_url
    - election_id
    - draft_election_administration_page_url
    """

    def setUp(self):
        self.fake_sent_emails_manager = FakeSentEmailsManager(settings.SENT_EMAILS_TEXT_FILE_ABSOLUTE_PATH)
        self.fake_sent_emails_manager.install_fake_sendmail_log_file()

        remove_database_folder()

        self.server = initialize_server()

        self.browser = initialize_browser_for_scenario_2()

        self.voters_email_addresses = []
        self.voters_email_addresses_who_have_lost_their_password = []
        self.voters_data = dict()
        self.election_page_url = None
        self.election_id = None

        self.draft_election_administration_page_url = None


    def tearDown(self):
        self.browser.quit()

        self.server.kill()

        remove_database_folder()

        self.fake_sent_emails_manager.uninstall_fake_sendmail_log_file()


    def administrator_starts_creation_of_manual_election(self):
        # # Setting up a new election (action of the administrator)

        browser = self.browser

        # Alice has been given administrator rights on an online voting app called Belenios. She goes
        # to check out its homepage and logs in
        log_in_as_administrator(browser)

        # She starts creation of the election:
        # - She clicks on the "Prepare a new election" link
        # - She picks the Credential management method: manual
        # (- She keeps default value for Authentication method: it is Password, not CAS)
        # - She clicks on the "Proceed" button (this redirects to the "Preparation of election" page)
        # - She changes values of fields name and description of the election
        # - She clicks on the "Save changes button" (the one that is next to the election description field)
        administrator_starts_creation_of_election(browser, True)

        # She remembers the URL of the draft election administration page
        self.draft_election_administration_page_url = browser.current_url

        # She edits election's questions:
        # - She clicks on the "Edit questions" link, to write her own questions
        # - She arrives on the Questions page. She checks that the page title is correct
        # - She removes answer 3
        # - She clicks on the "Save changes" button (this redirects to the "Preparation of election" page)
        administrator_edits_election_questions(browser)

        # She sets election's voters:
        # - She clicks on the "Edit voters" link, to then type the list of voters
        # - She types N e-mail addresses (the list of invited voters)
        # - She clicks on the "Add" button to submit changes
        # - She clicks on "Return to draft page" link
        self.voters_email_addresses = random_email_addresses_generator(settings.NUMBER_OF_INVITED_VOTERS)
        administrator_sets_election_voters(browser, self.voters_email_addresses)

        # In "Authentication" section, she clicks on the "Generate and mail missing passwords" button
        generate_and_mail_missing_passwords_button_label = "Generate and mail missing passwords"
        generate_and_mail_missing_passwords_button_element = wait_for_element_exists(browser, build_css_selector_to_find_buttons_in_page_content_by_value(generate_and_mail_missing_passwords_button_label), settings.EXPLICIT_WAIT_TIMEOUT)
        generate_and_mail_missing_passwords_button_element.click()

        wait_a_bit()

        # She checks that the page contains expected confirmation text, instead of an error (TODO: explain in which case an error can happen, and check that it does not show)
        confirmation_sentence_expected_text = "Passwords have been generated and mailed!"
        confirmation_sentence_css_selector = "#main p"
        wait_for_element_exists_and_contains_expected_text(browser, confirmation_sentence_css_selector, confirmation_sentence_expected_text, settings.EXPLICIT_WAIT_TIMEOUT)

        # She clicks on the "Proceed" link (this redirects to the "Preparation of election" page)
        proceed_link_expected_label = "Proceed"
        proceed_link_css_selector = "#main a"
        proceed_link_element = wait_for_element_exists_and_contains_expected_text(browser, proceed_link_css_selector, proceed_link_expected_label, settings.EXPLICIT_WAIT_TIMEOUT)
        proceed_link_element.click()

        wait_a_bit()

        # In "Credentials" section, she clicks on "Credential management" link
        credential_management_expected_label = "Credential management"
        credential_management_link_element = wait_for_an_element_with_partial_link_text_exists(browser, credential_management_expected_label)
        credential_management_link_element.click()

        wait_a_bit()

        # She remembers the link displayed
        link_for_credential_authority_css_selector = "#main a"
        link_for_credential_authority_element = wait_for_element_exists_and_has_non_empty_content(browser, link_for_credential_authority_css_selector)
        link_label = link_for_credential_authority_element.get_attribute('innerText').strip()
        self.credential_authority_link = link_label

        # She sends the remembered link to the credential authority by email (actually we don't need to send anything because we will act as the credential authority)

        # She closes the browser
        browser.quit()


    def credential_authority_sends_credentials_to_voters(self):
        # Cecily, the Credential Authority, receives the email sent by Alice, and opens the link in it
        self.browser = initialize_browser_for_scenario_2()
        browser = self.browser
        browser.get(self.credential_authority_link)

        wait_a_bit()

        # She remembers what the link to the election will be, so that she will be able to send it to voters by email with their private credential
        # TODO: use a better selector: edit Belenios page to use an ID in this DOM element
        future_election_link_css_selector = "#main ul li"
        future_election_link_element = wait_for_element_exists_and_has_non_empty_content(browser, future_election_link_css_selector)
        self.election_page_url = future_election_link_element.get_attribute('innerText').strip()

        # She clicks on the "Generate" button
        generate_button_css_selector = "#interactivity button"
        generate_button_element = wait_for_element_exists(browser, generate_button_css_selector)
        generate_button_element.click()

        wait_a_bit()

        # She clicks on the "private credentials" link and downloads the file. File goes to /tmp/creds.txt
        download_private_credentials_link_css_selector = "#creds"
        download_private_credentials_link_element = wait_for_element_exists(browser, download_private_credentials_link_css_selector)
        download_private_credentials_link_element.click()

        wait_a_bit()

        # She clicks on the "public credentials" link and downloads the file. File goes to /tmp/public_creds.txt
        download_public_credentials_link_css_selector = "#public_creds"
        download_public_credentials_element = wait_for_element_exists(browser, download_public_credentials_link_css_selector)
        download_public_credentials_element.click()

        wait_a_bit()

        # She clicks on the "Submit public credentials" button
        submit_button_css_selector = "#submit_form input[type=submit]"
        submit_button_element = wait_for_element_exists(browser, submit_button_css_selector)
        submit_button_element.click()

        wait_a_bit()

        # She checks that redirected page shows correct confirmation sentence
        expected_content_text = "Credentials have been received and checked!"
        expected_content_css_selector = "#main"
        wait_for_element_exists_and_contains_expected_text(browser, expected_content_css_selector, expected_content_text)

        wait_a_bit()

        # She closes the window
        browser.quit()

        # She reads the private credentials file (creds.txt) and sends credential emails to voters
        # TODO: Should we check that creds.txt contains the exact same voters email addresses as the ones that admin has added?
        private_credentials_file_path = os.path.join(settings.BROWSER_DOWNLOAD_FOLDER, "creds.txt")
        from_email_address = settings.CREDENTIAL_AUTHORITY_EMAIL_ADDRESS
        subject = "Your credential for election " + settings.ELECTION_TITLE
        content = """You are listed as a voter for the election

  {election_title}

You will find below your credential.  To cast a vote, you will also
need a password, sent in a separate email.  Be careful, passwords and
credentials look similar but play different roles.  You will be asked
to enter your credential before entering the voting booth.  Login and
passwords are required once your ballot is ready to be cast.

Credential: {credential}
Page of the election: {election_url}

Note that you are allowed to vote several times.  Only the last vote
counts."""
        with open(private_credentials_file_path) as myfile:
            for line in myfile:
                match = re.search(r'^(\S+)\s(\S+)$', line)
                if match:
                    voter_email_address = match.group(1)
                    voter_private_credential = match.group(2)
                else:
                    raise Exception("File creds.txt has wrong format")
            custom_content = content.format(election_title=settings.ELECTION_TITLE, credential=voter_private_credential, election_url=self.election_page_url)
            self.fake_sent_emails_manager.send_email(from_email_address, voter_email_address, subject, custom_content)


    def administrator_invites_trustees(self):
        self.browser = initialize_browser_for_scenario_2()
        browser = self.browser

        log_in_as_administrator(browser)

        browser.get(self.draft_election_administration_page_url)

        wait_a_bit()

        # In the trustees section, she clicks on the "here" link
        # TODO: use a better selector: edit Belenios page to use an ID in this DOM element
        setup_election_key_link_label = "here"
        setup_election_key_link_element = wait_for_an_element_with_partial_link_text_exists(browser, setup_election_key_link_label)
        setup_election_key_link_element.click()

        wait_a_bit()

        # She adds two trustees (their email address), and remembers the link she will send to each trustee
        links_for_trustees = []
        email_address_field_css_selector = "#main form input[type=text]"
        submit_button_css_selector = "#main form input[type=submit][value=Add]"

        for idx, email_address in enumerate(settings.TRUSTEES_EMAIL_ADDRESSES):
            email_address_field_element = wait_for_element_exists(browser, email_address_field_css_selector)
            email_address_field_element.clear()
            email_address_field_element.send_keys(email_address)

            submit_button_element = wait_for_element_exists(browser, submit_button_css_selector)
            submit_button_element.click()

            trustee_link_css_selector = "#main table tr:nth-child(" + str(idx+2) + ") td:nth-child(3) a"
            trustee_link_element = wait_for_element_exists_and_has_non_empty_content(browser, trustee_link_css_selector)
            links_for_trustees.append(trustee_link_element.get_attribute('href'))

            wait_a_bit()

        # She sends to each trustee an email containing their own link
        subject = "Link to generate the decryption key"
        content_format = """\
Dear trustee,

You will find below the link to generate your private decryption key, used to tally the election.

{link_for_trustee}

Here's the instructions:
1. click on the link
2. click on "generate a new key pair"
3. your private key will appear in another window or tab. Make sure
you SAVE IT properly otherwise it will not possible to tally and the
election will be canceled.
4. in the first window, click on "submit" to send the public part of
your key, used encrypt the votes. For verification purposes, you
should save this part (that starts with "pok" "challenge"), for
example sending yourself an email.

Regarding your private key, it is crucial you save it (otherwise the
election will be canceled) and store it securely (if your private key
is known together with the private keys of the other trustees, then
vote privacy is no longer guaranteed). We suggest two options:
1. you may store the key on a USB stick and store it in a safe.
2. Or you may simply print it and store it in a safe.
Of course, more cryptographic solutions are welcome as well.

Thank you for your help,

--
The election administrator.\
"""
        for idx, trustee_email_address in enumerate(settings.TRUSTEES_EMAIL_ADDRESSES):
            custom_content = content_format.format(link_for_trustee=links_for_trustees[idx])
            self.fake_sent_emails_manager.send_email(settings.ADMINISTRATOR_EMAIL_ADDRESS, trustee_email_address, subject, custom_content)

        # She closes the window
        browser.quit()


    def trustees_generate_election_private_keys(self):
        for idx, trustee_email_address in enumerate(settings.TRUSTEES_EMAIL_ADDRESSES):
            pass
        # TODO: implement this section


    def test_scenario_2_manual_vote(self):
        console_log("### Starting step: administrator_starts_creation_of_manual_election")
        self.administrator_starts_creation_of_manual_election()
        console_log("### Step complete: administrator_starts_creation_of_manual_election")

        console_log("### Starting step: credential_authority_sends_credentials_to_voters")
        self.credential_authority_sends_credentials_to_voters()
        console_log("### Step complete: credential_authority_sends_credentials_to_voters")

        console_log("### Starting step: administrator_invites_trustees")
        self.administrator_invites_trustees()
        console_log("### Step complete: administrator_invites_trustees")

        console_log("### Starting step: trustees_generate_election_private_keys")
        self.trustees_generate_election_private_keys()
        console_log("### Step complete: trustees_generate_election_private_keys")

        # TODO: Continue implementation of Scenario 2


if __name__ == "__main__":
    random_seed = os.getenv('RANDOM_SEED', None)
    if not random_seed:
        random_seed = random.randrange(sys.maxsize)
    console_log("Python random seed being used:", random_seed)
    random.seed(random_seed)

    if os.getenv('USE_HEADLESS_BROWSER', None):
        settings.USE_HEADLESS_BROWSER = bool(strtobool(os.getenv('USE_HEADLESS_BROWSER')))

    settings.SENT_EMAILS_TEXT_FILE_ABSOLUTE_PATH = os.getenv('SENT_EMAILS_TEXT_FILE_ABSOLUTE_PATH', settings.SENT_EMAILS_TEXT_FILE_ABSOLUTE_PATH)
    settings.WAIT_TIME_BETWEEN_EACH_STEP = float(os.getenv('WAIT_TIME_BETWEEN_EACH_STEP', settings.WAIT_TIME_BETWEEN_EACH_STEP))
    settings.EXPLICIT_WAIT_TIMEOUT = int(os.getenv('EXPLICIT_WAIT_TIMEOUT', settings.EXPLICIT_WAIT_TIMEOUT))
    settings.NUMBER_OF_INVITED_VOTERS = int(os.getenv('NUMBER_OF_INVITED_VOTERS', settings.NUMBER_OF_INVITED_VOTERS))
    settings.NUMBER_OF_VOTING_VOTERS = int(os.getenv('NUMBER_OF_VOTING_VOTERS', settings.NUMBER_OF_VOTING_VOTERS))
    settings.NUMBER_OF_REVOTING_VOTERS = int(os.getenv('NUMBER_OF_REVOTING_VOTERS', settings.NUMBER_OF_REVOTING_VOTERS))
    settings.NUMBER_OF_REGENERATED_PASSWORD_VOTERS = int(os.getenv('NUMBER_OF_REGENERATED_PASSWORD_VOTERS', settings.NUMBER_OF_REGENERATED_PASSWORD_VOTERS))
    settings.ADMINISTRATOR_USERNAME = os.getenv('ADMINISTRATOR_USERNAME', settings.ADMINISTRATOR_USERNAME)
    settings.ADMINISTRATOR_PASSWORD = os.getenv('ADMINISTRATOR_PASSWORD', settings.ADMINISTRATOR_PASSWORD)
    settings.ELECTION_TITLE = os.getenv('ELECTION_TITLE', settings.ELECTION_TITLE)
    settings.ELECTION_DESCRIPTION = os.getenv('ELECTION_DESCRIPTION', settings.ELECTION_DESCRIPTION)
    settings.BROWSER_DOWNLOAD_FOLDER = os.getenv('BROWSER_DOWNLOAD_FOLDER', settings.BROWSER_DOWNLOAD_FOLDER)
    settings.ADMINISTRATOR_EMAIL_ADDRESS = os.getenv('ADMINISTRATOR_EMAIL_ADDRESS', settings.ADMINISTRATOR_EMAIL_ADDRESS)
    settings.CREDENTIAL_AUTHORITY_EMAIL_ADDRESS = os.getenv('CREDENTIAL_AUTHORITY_EMAIL_ADDRESS', settings.CREDENTIAL_AUTHORITY_EMAIL_ADDRESS)
    # TODO: settings.TRUSTEES_EMAIL_ADDRESSES (it cannot be manipulated the same way because it is an array)

    console_log("USE_HEADLESS_BROWSER:", settings.USE_HEADLESS_BROWSER)
    console_log("SENT_EMAILS_TEXT_FILE_ABSOLUTE_PATH:", settings.SENT_EMAILS_TEXT_FILE_ABSOLUTE_PATH)
    console_log("WAIT_TIME_BETWEEN_EACH_STEP:", settings.WAIT_TIME_BETWEEN_EACH_STEP)
    console_log("EXPLICIT_WAIT_TIMEOUT:", settings.EXPLICIT_WAIT_TIMEOUT)
    console_log("NUMBER_OF_INVITED_VOTERS:", settings.NUMBER_OF_INVITED_VOTERS)
    console_log("NUMBER_OF_VOTING_VOTERS:", settings.NUMBER_OF_VOTING_VOTERS)
    console_log("NUMBER_OF_REVOTING_VOTERS:", settings.NUMBER_OF_REVOTING_VOTERS)
    console_log("NUMBER_OF_REGENERATED_PASSWORD_VOTERS:", settings.NUMBER_OF_REGENERATED_PASSWORD_VOTERS)
    console_log("ELECTION_TITLE:", settings.ELECTION_TITLE)
    console_log("ELECTION_DESCRIPTION:", settings.ELECTION_DESCRIPTION)
    console_log("BROWSER_DOWNLOAD_FOLDER:", settings.BROWSER_DOWNLOAD_FOLDER)
    console_log("ADMINISTRATOR_EMAIL_ADDRESS:", settings.ADMINISTRATOR_EMAIL_ADDRESS)
    console_log("CREDENTIAL_AUTHORITY_EMAIL_ADDRESS:", settings.CREDENTIAL_AUTHORITY_EMAIL_ADDRESS)
    console_log("TRUSTEES_EMAIL_ADDRESSES:", settings.TRUSTEES_EMAIL_ADDRESSES)

    unittest.main()
