# -*- coding: utf-8 -*-

# Copyright (c) 2015, Brendan Quinn, Clueful Media Ltd / JT-PATS Ltd
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
PATS Python library - Buyer side - Brendan Quinn Dec 2014

Based on Mediaocean PATS API documented at https://developer.mediaocean.com/
"""

from collections import OrderedDict
from httplib import HTTPSConnection
import base64
import datetime
import json
import os
import re
import string
import types
from urllib import urlencode
from .core import PATSAPIClient, PATSException, CampaignDetails, InsertionOrderDetails

AGENCY_API_DOMAIN = 'prisma-demo.api.mediaocean.com'

class PATSBuyer(PATSAPIClient):
    agency_id = None

    def __init__(self, agency_id=None, api_key=None, debug_mode=False, raw_mode=False, session=None):
        """
        Create a new buyer-side PATS API object.

        Parameters:
        - agency_id (required) : ID of the agency (buyer) whose catalogue
          you are updating.
        - api_key (required) : API Key with buyer access
        - debug_mode (boolean) : Output full details of HTTP requests and responses
        - raw_mode (boolean) : Store output of request (as 'curl' equivalent) and
                               response (JSON payload) when making requests
        - session (optional) : User session in which to write curl and response objects in raw mode
        """
        super(PATSBuyer, self).__init__(api_key, debug_mode, raw_mode, session)
        if agency_id == None:
            raise PATSException("Agency (aka buyer) ID is required")
        self.agency_id = agency_id

    def get_sellers(self, user_id=None):
        """
        As a buyer, view all the sellers for which I have access to send orders.
        http://developer.mediaocean.com/docs/read/organization_api/Get_seller_organization
        """
        if user_id == None:
            raise PATSException("User ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.security-v1+json',
            'X-MO-User-ID': user_id
        }
        path = '/vendors?agencyId=%s' % self.agency_id
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def get_buyers(self, user_id=None, agency_id=None, name=None, last_updated_date=None):
        """
        As a buyer user, list the details of all agencies I represent.
        http://developer.mediaocean.com/docs/read/organization_api/Get_agency
        """
        if user_id == None:
            raise PATSException("User ID is required")
        if agency_id == None:
            # use default agency ID if none specified
            agency_id = self.agency_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.security-v1+json',
            'X-MO-User-ID': user_id,
        }
        path = '/agencies?agencyId=%s' % agency_id
        if name:
            path += "&name=%s" % name
        if last_updated_date:
            path += "&lastUpdatedDate=%s" % last_updated_date
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        return js


    def get_users_for_seller(self, user_id=None, vendor_id=None):
        """
        As a buyer, view all the sellers to whom I can send orders at the
        given vendor.
        http://developer.mediaocean.com/docs/read/organization_api/Get_user
        """
        if user_id == None:
            raise PATSException("User ID is required")
        if vendor_id == None:
            raise PATSException("Vendor ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.security-v1+json',
            'X-MO-User-ID': user_id
        }
        path = '/users?appName=pats&agencyId=%s&vendorId=%s' % (self.agency_id, vendor_id)
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def create_campaign(self, campaign_details=None, **kwargs):
        """
        Create an agency-side campaign, which is then used to send RFPs and orders.
        "campaign_details" must be a CampaignDetails instance.
        http://developer.mediaocean.com/docs/read/prisma_integration_api/Create_campaign
        """
        if not isinstance(campaign_details, CampaignDetails):
            raise PATSException(
                "The campaign_details parameter should be a CampaignDetails instance"
            )

        # Create the http object
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Company-ID': campaign_details.company_id,
            'X-MO-Organization-ID': campaign_details.organisation_id
        }
        # person_id is supposed to be optional - currently it fails without it though - PATS-1013
        if campaign_details.person_id:
            extra_headers.update({
                'X-MO-Person-ID': campaign_details.person_id,
            })
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/campaigns",
            extra_headers,
            campaign_details.json_repr()
        )
        # return full js object so we can parse errors
        return js

    def update_campaign(self, campaign_id=None, campaign_details=None):
        """
        We can PUT to the same endpoint to update the record - an almost RESTful API!
        http://developer.mediaocean.com/docs/read/prisma_integration_api/Create_campaign
        """
        if not isinstance(campaign_details, CampaignDetails):
            raise PATSException(
                "The campaign_details parameter should be a CampaignDetails instance"
            )
        if not campaign_id:
            raise PATSException("campaign_id is required")
        # Create the http object
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Person-ID': campaign_details.person_id,
            'X-MO-Company-ID': campaign_details.company_id,
            'X-MO-Organization-ID': campaign_details.organisation_id
        }
        js = self._send_request(
            "PUT",
            AGENCY_API_DOMAIN,
            "/campaigns/%s" % campaign_id,
            extra_headers,
            campaign_details.json_repr()
        )
        # return full js object so we can parse errors
        return js

    def view_campaign_detail(self, sender_user_id, campaign_public_id):
        """
        There's no specific API to view a campaign, so we have to use
        "view RFPs for campaign"
        http://developer.mediaocean.com/docs/read/rfp_api/Get_rfps_by_camp_publicid
        """
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/campaigns/%s/rfps" % (self.agency_id, campaign_public_id),
            extra_headers
        )
        return js

    def submit_rfp(self, sender_user_id=None, campaign_public_id=None, budget_amount=None, budgets=None, start_date=None, end_date=None, respond_by_date=None, comments="", publisher_id=None, publisher_emails=None, publishers=None, media_print=None, media_online=None, strategy=None, requested_products=None, attachments=None):
        """
        Send an RFP to one or more publishers.
        Can optionally include product IDs.
        http://developer.mediaocean.com/docs/read/rfp_api/Submit_rfp
        """
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        media = []
        if media_print:
            media.append('Print')
        if media_online:
            media.append('Online')
        data = {
            'agencyPublicId': self.agency_id,
            'campaignPublicId': campaign_public_id,
            'startDate': start_date.strftime("%Y-%m-%d"),
            'endDate': end_date.strftime("%Y-%m-%d"),
            'responseDueDate': respond_by_date.strftime("%Y-%m-%d"),
            'comments': comments,
            'media': media,
            'strategy': strategy # must be one of defined set of terms
        }
        # user can supply "budget_amount" with one budget or "budgets" with a list
        if budget_amount:
            data.update({ 'budgets': [ budget_amount ] })
        elif (budgets and type(budgets) is types.ListType):
            data.update({'budgets': budgets})
        else:
            raise PATSException("Either budget_amount (single value) or budgets (list) is required")
        # user can supply "publisher_id" and "publisher_emails" for one publisher, or "publishers"
        # with a dict for multiple publishers
        if publisher_id and publisher_emails:
            data.update({
                'publisherRecipients': [
                    {
                        'publisherPublicId': publisher_id,
                        'emails': publisher_emails,
                    }
                ]
            })
        elif publishers:
            data.update({
                'publisherRecipients': publishers
            })
            
        if requested_products and requested_products != '':
            data.update({'requestedProducts': requested_products })
        # handle attachments - expect an array containing dicts
        # of { "fileName", "mimeType" and "contents" }
        if attachments:
            data.update({ 'attachments': attachments })
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/agencies/%s/campaigns/%s/rfps" % (self.agency_id, campaign_public_id),
            extra_headers,
            json.dumps(data)
        )
        return js

    def view_rfp_detail(self, sender_user_id=None, rfp_id=None):
        """
        Get a single RFP using its public ID.
        http://developer.mediaocean.com/docs/read/rfp_api/Get_rfp_by_publicid
        """
        if rfp_id is None:
            raise PATSException("RFP ID is required")
        if sender_user_id is None:
            raise PATSException("Sender User ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/rfps/%s" % (self.agency_id, rfp_id),
            extra_headers
        )
        return js

    def get_rfp_attachment(self, sender_user_id=None, rfp_id=None, attachment_id=None):
        """
        Get an attachment from an RFP.
        http://developer.mediaocean.com/docs/read/rfp_api/Get_rfp_attachment_by_publicid
        """
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/rfps/%s/attachments/%s" % (self.agency_id, rfp_id, attachment_id),
            extra_headers
        )
        return js

    def search_rfps(self, user_id=None, advertiser_name=None, campaign_urn=None, rfp_start_date=None,rfp_end_date=None,response_due_date=None,status=None):
        """
        Search for RFPs by advertiser name, campaign ID, RFP dates, response due date and/or status.
        http://developer.mediaocean.com/docs/read/rfp_api/Search_for_rfps
        """
        # /agencies/35-1-1W-1/rfps?advertiserName=Jaguar Land Rover&campaignUrn=someUrn&rfpStartDate=2014-08-10&rfpEndDate=2015-01-10&responseDueDate=2015-08-25&status=SENT
        if user_id is None:
            raise PATSException("User ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': user_id
        }
        path = '/agencies/%s/rfps' % self.agency_id
        if advertiser_name or campaign_urn or rfp_start_date or rfp_end_date or response_due_date or status:
            path += "?"
        if advertiser_name:
            path += "advertiserName=%s&" % advertiser_name
        if campaign_urn:
            path += "campaignUrn=%s&" % campaign_urn
        if rfp_start_date:
            path += "rfpStartDate=%s&" % rfp_start_date
        if rfp_end_date:
            path += "rfpEndDate=%s&" % rfp_end_date
        if response_due_date:
            path += "responseDueDate=%s&" % response_due_date
        if status:
            path += "status=%s&" % status

        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def get_proposal_attachment(self, sender_user_id=None, proposal_id=None, attachment_id=None):
        """
        Get contents of proposal attachment based on the proposal ID.
        http://developer.mediaocean.com/docs/read/rfp_api/Get_proposal_attachment_by_publicid
        """
        if sender_user_id is None:
            raise PATSException("Sender-User-ID is required")
        if proposal_id is None:
            raise PATSException("Proposal ID is required")
        if attachment_id is None:
            raise PATSException("Attachment ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/proposals/%s/attachments/%s" % (self.agency_id, proposal_id, attachment_id),
            extra_headers
        )
        return js

    def return_proposal(self, sender_user_id=None, proposal_public_id=None, comments=None, due_date=None, emails=None, attachments=None):
        """
        "Return a proposal", which means "send a comment back to the seller that sent me this proposal"
        http://developer.mediaocean.com/docs/read/rfp_api/Return_proposal
        """
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        if proposal_public_id is None:
            raise PATSException("Proposal ID is required")
        data = {
            'comments': comments,
            'dueDate': due_date.strftime("%Y-%m-%d"),
            'emails': emails
        }
        if attachments:
            data.update({
                'attachments': attachments
            })
        js = self._send_request(
            "PUT",
            AGENCY_API_DOMAIN,
            "/agencies/%s/proposals/%s/return" % (self.agency_id, proposal_public_id),
            extra_headers,
            json.dumps(data)
        )
        return js

    def list_products(self, vendor_id=None, user_id=None, start_index=None, max_results=None, include_logo=False):
        """
        List products in a vendor's product catalogue.

        The parameters are :
        - vendor_id (required): ID of the vendor (publisher) whose catalogue
          you are requesting.
        - start_index (optional): First product to load (if doing paging)
        - max_results (optional):

        http://developer.mediaocean.com/docs/read/catalog_api/List_catalog_products
        """
        if vendor_id is None:
            raise PATSException("Vendor ID is required")
        if user_id is None:
            raise PATSException("User ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.catalog-v1+json',
            'X-MO-User-Id': user_id
        }

        params = {}
        if start_index:
            params.update({'start_index' : start_index})
        if max_results:
            params.update({'max_results' : max_results})
        if include_logo:
            params.update({'include_logo' : include_logo})
        params = urlencode(params)

        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/vendors/%s/products/?%s" % (self.agency_id, vendor_id, params),
            extra_headers
        )
        # result looks like
        # {"total":117,"products":[{"vendorPublicId":"35-EEBMG4J-4","productPublicId":"PC-11TU", ... }
        return js

    def create_order(self, **kwargs):
        """
        create a print or digital order in PATS.
        agency_id: PATS ID of the buying agency (eg 35-IDSDKAD-7)
        company_id: PATS ID of the buying company (eg PATS3)
        person_id: (optional?) PATS ID of the person sending the order (different
            from the person named as the buyer contact in the order)
        insertion_order_details: info about the insertion order (must be an InsertionOrderDetails object)
        line_items: object inserted as "line_items" in the order

        http://developer.mediaocean.com/docs/read/orders_api/Create_online_order
        http://developer.mediaocean.com/docs/read/orders_api/Create_print_order
        """
        # has default but can be overridden
        agency_id = kwargs.get('agency_id', self.agency_id)
        if kwargs.get('company_id') == None:
            raise PATSException("Company ID is required")
        company_id = kwargs.get('company_id')
        # person_id is optional
        person_id = kwargs.get('person_id', None)
        if kwargs.get('insertion_order_details') == None:
            raise PATSException("Insertion Order object is required")
        insertion_order = kwargs.get('insertion_order_details', None)
        if not isinstance(insertion_order, InsertionOrderDetails):
            raise PATSException("insertion_order_details must be an instance of InsertionOrderDetails")

        # order payload
        data = {
            'externalCampaignId':kwargs.get('external_campaign_id', None),
            'mediaType':kwargs.get('media_type', 'PRINT'),
            'insertionOrder':insertion_order.dict_repr()
        }
        # technically line items are optional!
        if kwargs.get('line_items'):
            line_items = []
            for line_item in kwargs['line_items']:
                if not line_item.operation:
                    line_item.setOperation('Add')
                line_items.append(line_item.dict_repr())
            data.update({
                'lineItems':line_items
            })

        return self.create_order_raw(agency_id=agency_id, company_id=company_id, person_id=person_id, data=data)

    def create_order_raw(self, agency_id=None, company_id=None, person_id=None, data=None):
        """
        create a print or digital order in PATS using a fully formed JSON payload
        instead of Python objects.

        agency_id: PATS ID of the buying agency (eg 35-IDSDKAD-7)
        company_id: PATS ID of the buying company (eg PATS3)
        person_id: (optional?) PATS ID of the person sending the order (different
            from the person named as the buyer contact in the order)
        data: full JSON payload - must contain campaign ID, insertion order details and all line items

        http://developer.mediaocean.com/docs/read/orders_api/Create_online_order
        http://developer.mediaocean.com/docs/read/orders_api/Create_print_order
        """
        if agency_id==None:
            agency_id=self.agency_id # default but can be overridden
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Company-ID': company_id,
            'X-MO-Organization-ID': agency_id
        }
        if person_id:
            extra_headers.update({
                'X-MO-Person-ID': person_id
            })

        # send request
        js = self._send_request(
            "PUT",
            AGENCY_API_DOMAIN,
            "/order/send",
            extra_headers,
            json.dumps(data)
        )
        return js

    def view_orders(self, user_id=None, start_date=None, end_date=None):
        """
        TODO - Mediaocean need to create an API for this!!
        """
        pass

    def view_order_revisions(self, user_id=None, start_date=None, end_date=None):
        """
        As a buyer, view all order revisions sent to me.
        http://developer.mediaocean.com/docs/read/orders_api/Get_orders [sic]
        """
        if start_date == None:
            raise PATSException("Start date is required")
        if not isinstance(start_date, datetime.datetime) and not (isinstance(start_date, datetime.date)):
            raise PATSException("Start date must be a Python date or datetime object")
        if not isinstance(end_date, datetime.datetime) and not (isinstance(end_date, datetime.date)):
            raise PATSException("If end date exists it must be a Python date or datetime object")
        if user_id == None:
            raise PATSException("User ID is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-User-Id': user_id
        }

        path = '/agencies/%s/orders/revisions' % self.agency_id
        if start_date and end_date:
            # not sure if you can have one or the other on its own?
            path += "?startDate=%s&endDate=%s" % (
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

    def view_order_detail(self, user_id=None, order_id=None):
        """
        As a buyer, view the detail of one order.

        http://developer.mediaocean.com/docs/read/orders_api/Get_order_detail
        """
        # /agencies/{agency public id}/orders/{External Order Id}/revisions
        if user_id == None:
            raise PATSException("User ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-User-Id': user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/orders/%s/revisions" % (self.agency_id, order_id),
            extra_headers
        )
        return js

    def view_order_status(self, person_id=None, company_id=None, campaign_id=None, order_id=None, version=None):
        """
        As a buyer, view the status of an order I have just sent.

        http://developer.mediaocean.com/docs/read/orders_api/Get_order_status
        """
        # /order/status/{externalCampaignId}/{orderId}/{version}
        if company_id == None:
            raise PATSException("Company ID is required")
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Company-ID': company_id,
            'X-MO-Organization-ID': self.agency_id
        }
        if person_id:
            extra_headers.update({
                'X-MO-Person-ID': person_id,
            })
        path = "/order/status/%s/%s" % (campaign_id, order_id)
        if version:
            path += "/"+version
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        return js
        
    def return_order_revision(self, order_public_id, order_major_version, order_minor_version, user_id, seller_email, revision_due_date, comment):
        """
        "Return order revision" which means "Send a message back to the person who sent this revision"

        http://developer.mediaocean.com/docs/read/orders_api/Return_revision
        """
        # TODO: allow attachments
        # /agencies/{agency public id}/orders/{external public id}/revisions/return 
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-User-ID': user_id
        }
        data = {
            'majorVersion': order_major_version,
            'minorVersion': order_minor_version,
            'revisionDueBy': revision_due_date.strftime("%Y-%m-%d"),
            'comment': comment,
            'email': seller_email,
            'orderAttachments': [], # leave it blank for now
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/agencies/%s/orders/%s/revisions/return" % (self.agency_id, order_public_id),
            extra_headers,
            json.dumps(data)
        )
        return js

    def request_order_revision(self, order_public_id=None, order_major_version=None, order_minor_version=None, user_id=None, seller_email=None, revision_due_date=None, comment=None):
        """
        "Request order revision" which means "Send a message to the person who received this order"
        http://developer.mediaocean.com/docs/read/orders_api/Request_order_revision
        """
        # TODO: allow attachments
        # /agencies/{agency public id}/orders/{External Order Id}/revisions/request
        extra_headers = {
            # might be 1.0 but I'm guessing that's another bug in the docs
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-User-ID': user_id
        }
        data = {
            'majorVersion': order_major_version,
            'minorVersion': order_minor_version,
            'revisionDueBy': revision_due_date.strftime("%Y-%m-%d"),
            'comment': comment,
            'email': seller_email,
            'orderAttachments': [], # leave it blank for now
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/agencies/%s/orders/%s/revisions/request" % (self.agency_id, order_public_id),
            extra_headers,
            json.dumps(data)
        )
        return js
