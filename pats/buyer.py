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
    agency_group_id = None
    user_id = None

    def __init__(self, agency_id=None, agency_group_id=None, user_id=None, api_key=None, debug_mode=False, raw_mode=False, session=None):
        """
        Create a new buyer-side PATS API object.

        Parameters:
        - agency_id (required) : ID of the agency (buyer) who your buy-side call represents.
        - agency_group_id (required) : ID of the agency (buyer) group.
        - user_id (optional) : User ID of the buyer user.
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
        self.agency_group_id = agency_group_id
        self.user_id = user_id

    def get_sellers(self, user_id=None):
        """
        As a buyer, view all the sellers for which I have access to send orders.
        http://developer.mediaocean.com/docs/read/organization_api/Get_seller_organization
        """
        if user_id == None:
            user_id = self.user_id

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
            user_id = self.user_id
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
            user_id = self.user_id
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

    def create_campaign(self, campaign_details=None, user_id=None, **kwargs):
        """
        Create an agency-side campaign, which is then used to send RFPs and orders.
        "campaign_details" must be a CampaignDetails instance.
        http://developer.mediaocean.com/docs/read/prisma_integration_api/Create_campaign
        """
        if not isinstance(campaign_details, CampaignDetails):
            raise PATSException(
                "The campaign_details parameter should be a CampaignDetails instance"
            )

        if campaign_details.user_id:
            user_id = campaign_details.user_id
        organisation_id = campaign_details.organisation_id or self.agency_id
        # Create the http object
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Agency-Group-ID': self.agency_group_id,
            'X-MO-Organization-ID': organisation_id,
            'X-MO-User-ID': user_id
        }
        campaign_uri = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/campaigns",
            extra_headers,
            campaign_details.json_repr()
        )
        # campaign_uri looks like https://prisma-devciny.api.mediaocean.com/campaigns/CP1D9G
        match = re.search('https://(.+)?/campaigns/(.+?)$', campaign_uri)
        if match:
            campaign_id = match.group(2) 
        return campaign_id

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
        organisation_id = campaign_details.organisation_id or self.agency_id
        # Create the http object
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-User-ID': campaign_details.user_id,
            'X-MO-Agency-Group-Id': self.agency_group_id,
            'X-MO-Organization-ID': organisation_id
        }
        response = self._send_request(
            "PUT",
            AGENCY_API_DOMAIN,
            "/campaigns/%s" % campaign_id,
            extra_headers,
            campaign_details.json_repr()
        )
        # used to return a js object, now it's just the URI of the object
        return response

    def view_campaign_detail(self, agency_group_id=None, agency_id=None, user_id=None, campaign_id=None):
        """
        In 2015.8, we don't have to use workarounds, there's a view campaign call
        """
        if agency_group_id is None:
            agency_group_id = self.agency_group_id
        if agency_id is None:
            agency_id = self.agency_id
        if user_id is None:
            user_id = self.user_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1+json',
            'X-MO-User-ID': user_id,
            'X-MO-App': 'prisma',
            'X-MO-Organization-ID': agency_id,
            'X-MO-Agency-Group-ID': agency_group_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/campaigns/%s" % (campaign_id),
            extra_headers
        )
        return js

    def submit_rfp(self, sender_user_id=None, agency_group_id=None, campaign_public_id=None, currency='GBP', budget_amount=None, budgets=None, start_date=None, end_date=None, respond_by_date=None, comments="", publisher_id=None, publisher_emails=None, publishers=None, media_print=None, media_online=None, strategy=None, requested_products=None, attachments=None):
        """
        Send an RFP to one or more publishers.
        Can optionally include product IDs.
        http://developer.mediaocean.com/docs/read/rfp_api/Submit_rfp
        """
        organisation_id = self.agency_id
        if agency_group_id is None:
            agency_group_id = self.agency_group_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-Organization-Id': organisation_id,
            'X-MO-Agency-Group-ID': agency_group_id,
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
            'currency': currency,
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

    def view_rfp_detail(self, agency_group_id=None, agency_id=None, user_id=None, rfp_id=None):
        """
        Get a single RFP using its public ID.
        http://developer.mediaocean.com/docs/read/rfp_api/Get_rfp_by_publicid
        """
        if rfp_id is None:
            raise PATSException("RFP ID is required")
        if user_id == None:
            user_id = self.user_id
        if agency_group_id is None:
            agency_group_id = self.agency_group_id
        if agency_id is None:
            agency_id = self.agency_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-Organization-ID': agency_id,
            'X-MO-Agency-Group-ID': agency_group_id,
            'X-MO-User-Id': user_id
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

    def search_rfps(self, agency_group_id=None, agency_id=None, user_id=None, advertiser_name=None, campaign_urn=None, rfp_start_date=None,rfp_end_date=None,response_due_date=None,status=None):
        """
        Search for RFPs by advertiser name, campaign ID, RFP dates, response due date and/or status.
        http://developer.mediaocean.com/docs/rfp_api/Search_for_rfps
        """
        # /agencies/35-1-1W-1/rfps?advertiserName=Jaguar Land Rover&campaignUrn=someUrn&rfpStartDate=2014-08-10&rfpEndDate=2015-01-10&responseDueDate=2015-08-25&status=SENT
        if user_id is None:
            user_id = self.user_id
        if agency_id is None:
            agency_id = self.agency_id
        if agency_group_id is None:
            agency_group_id = self.agency_group_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-Organization-Id': agency_id,
            'X-MO-Agency-Group-Id': agency_group_id,
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

    def return_proposal(self, agency_group_id=None, agency_id=None, sender_user_id=None, proposal_public_id=None, comments=None, due_date=None, emails=None, attachments=None):
        """
        "Return a proposal", which means "send a comment back to the seller that sent me this proposal"
        http://developer.mediaocean.com/docs/read/rfp_api/Return_proposal
        """
        if agency_group_id is None:
            agency_group_id = self.agency_group_id
        if agency_id is None:
            agency_id = self.agency_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id,
            'X-MO-Agency-Group-ID': agency_group_id,
            'X-MO-Organization-ID': agency_id,
            'X-MO-App': 'prisma'
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
            user_id = self.user_id

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

    def create_order(self, agency_id=None, agency_group_id=None, user_id=None, campaign_id=None, media_type=None, currency_code=None, external_order_id=None, vendor_id=None, recipient_emails=None, buyer_dict=None, notify_emails=None, additional_info=None, order_comment=None, respond_by_date=None, terms_and_conditions_name=None, terms_and_conditions_content=None, digital_line_items=None, print_line_items=None, **kwargs):
        """
        Create a print or digital order in PATS.
        agency_id: PATS ID of the buying agency (eg 35-IDSDKAD-7)
        agency_group_id: PATS ID of the buying company (eg PATS3)
        user_id: (optional?) PATS ID of the person sending the order (different
            from the person named as the buyer contact in the order)
        media_type: Either 'Print' or 'Online'
        campaign_id: campaign to which to attach this order
        digital_line_items: object inserted as "line_items" in the order
        print_line_items: object inserted as "line_items" in the order

        http://developer.mediaocean.com/docs/buyer_orders/Send_order_buyer
        http://developer.mediaocean.com/docs/buyer_orders/Buyer_orders_ref#order_version
        http://developer.mediaocean.com/docs/buyer_orders/Buyer_orders_ref#digital
        http://developer.mediaocean.com/docs/buyer_orders/Buyer_orders_ref#print
        """
        # has default but can be overridden
        if agency_id == None:
            agency_id = self.agency_id
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if user_id == None:
            user_id = kwargs.get('user_id', None)

        # order payload
        data = {
            "externalId": external_order_id,
            "mediaType": media_type,
            "currencyCode": currency_code,
            "vendorId": vendor_id,
            "recipientEmails": recipient_emails,
            "buyer": buyer_dict,
            "notifyEmails": notify_emails,
            "additionalInfo": additional_info,
            "comment": order_comment,
            "respondByDate": respond_by_date.strftime("%Y-%m-%d"),
            "termsAndConditions": {
                "name": terms_and_conditions_name,
                "content": terms_and_conditions_content
            }
        }
        # technically line items are optional!
        line_items = []
        if media_type == 'Online':
            for line_item in digital_line_items:
                line_items.append(line_item.dict_repr())
            data.update({
                'digitalLineItems':line_items
            })
        else:
            for line_item in print_line_items:
                line_items.append(line_item.dict_repr())
            data.update({
                'printLineItems':line_items
            })
        return self.create_order_raw(agency_id=agency_id, agency_group_id=agency_group_id, user_id=user_id, campaign_id=campaign_id, data=data)

    def create_order_raw(self, agency_id=None, agency_group_id=None, user_id=None, campaign_id=None, order_id=None, data=None):
        """
        create a print or digital order in PATS using a fully formed JSON payload
        instead of Python objects.

        agency_id: PATS ID of the buying agency (eg 35-IDSDKAD-7)
        agency_group_id: PATS ID of the buying company (eg PATS3)
        person_id: (optional?) PATS ID of the person sending the order (different
            from the person named as the buyer contact in the order)
        campaign_id: PATS Campaign ID (eg CXFQ) to which this order is being added
        order_id (optional): if supplied, this order is treated as a re-send of an existing order
        data: full JSON payload - must contain campaign ID, insertion order details and all line items

        http://developer.mediaocean.com/docs/buyer_orders/Send_order_buyer
        http://developer.mediaocean.com/docs/buyer_orders/Buyer_orders_ref#order_version
        http://developer.mediaocean.com/docs/buyer_orders/Buyer_orders_ref#digital
        http://developer.mediaocean.com/docs/buyer_orders/Buyer_orders_ref#print

        http://developer.mediaocean.com/docs/buyer_orders/Resend_order_buyer
        """
        if agency_id==None:
            agency_id=self.agency_id
        if agency_group_id==None:
            agency_group_id=self.agency_group_id
        if campaign_id==None:
            raise PATSException("Campaign ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-Agency-Group-ID': agency_group_id,
            'X-MO-Organization-ID': agency_id,
            'X-MO-App': 'prisma'
        }
        if user_id:
            extra_headers.update({
                'X-MO-User-ID': user_id
            })

        if order_id:
            path = "/campaigns/%s/orders/%s/versions" % (campaign_id, order_id)
        else:
            path = "/campaigns/%s/orders" % campaign_id

        # send request - as it returns 201 Created on success, _send_request parses out the Location header and returns the full location
        order_uri = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            path,
            extra_headers,
            json.dumps(data)
        )
        match = re.search('https?://(.+)?/campaigns/(.+?)/orders/(.+?)/versions/0$', order_uri)
        order_id = None
        if match:
            order_id = match.group(3)
        return order_id

    def list_orders(self, agency_id=None, agency_group_id=None, user_id=None, since_date=None, page_size=25, page=1):
        """
        Retrieve a list of all orders booked since "since_date" (new in 2015.8)

        http://developer.mediaocean.com/docs/buyer_orders/Find_orders_buyer
        """
        if since_date == None:
            raise PATSException("Since date is required")
        if not isinstance(since_date, datetime.datetime) and not (isinstance(since_date, datetime.date)):
            raise PATSException("Since date must be a Python date or datetime object")
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if agency_id == None:
            agency_id = self.agency_id
        if user_id == None:
            user_id = self.user_id
        path = '/orders?since=%s&size=%s&page=%s' % (since_date.strftime("%Y-%m-%d"), page_size, page)
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Agency-Group-ID': agency_group_id,
            'X-MO-Organization-ID': agency_id
        }
        if user_id:
            extra_headers.update({
                'X-MO-User-ID': user_id
            })

        # send request
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def list_all_orders(self, since_date=None):
        """
        Loop over the list_orders method until we definitely have all orders in an array
        """
        page_size = 25
        page = 1
        full_json_list = []
        remaining_content = True
        while (remaining_content):
            partial_json_list = self.list_orders(since_date=since_date, page_size=page_size, page=page)
            full_json_list.extend(partial_json_list)
            page = page + 1
            remaining_content = (len(partial_json_list) == page_size)

        return full_json_list

    def list_order_revisions(self, agency_id=None, agency_group_id=None, user_id=None, campaign_id=None, order_id=None, version=None):
        """
        As a buyer, list all revisions on a given order version.
        (Note than in 2015.7 and previous, this would list *all* order revisions)
        
        http://developer.mediaocean.com/docs/buyer_orders/List_order_revs_buyer
        """
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if agency_id == None:
            agency_id = self.agency_id
        if user_id == None:
            user_id = self.user_id

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Organization-Id': agency_id,
            'X-MO-Agency-Group-Id': agency_group_id,
            'X-MO-User-Id': user_id
        }

        path = '/campaigns/%s/orders/%s/versions/%s/revisions' % (campaign_id, order_id, version)
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        return js

    def list_order_versions(self, user_id=None, agency_id=None, agency_group_id=None, campaign_id=None, order_id=None):
        """
        As a buyer, list versions of an order.

        http://developer.mediaocean.com/docs/buyer_orders/List_order_versions_buyer
        """
        if user_id == None:
            user_id = self.user_id
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if agency_id == None:
            agency_id = self.agency_id

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Organization-Id': agency_id,
            'X-MO-Agency-Group-Id': agency_group_id,
            'X-MO-User-Id': user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/campaigns/%s/orders/%s/versions" % (campaign_id, order_id),
            extra_headers
        )
        return js


    def view_order_version_detail(self, user_id=None, agency_id=None, agency_group_id=None, campaign_id=None, order_id=None, version=None):
        """
        As a buyer, view the detail of one order version.

        http://developer.mediaocean.com/docs/buyer_orders/Get_order_version_details_buyer
        """
        if user_id == None:
            user_id = self.user_id
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if version == None:
            raise PATSException("Order version is required")
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if agency_id == None:
            agency_id = self.agency_id

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Organization-Id': agency_id,
            'X-MO-Agency-Group-Id': agency_group_id,
            'X-MO-User-Id': user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/campaigns/%s/orders/%s/versions/%s" % (campaign_id, order_id, version),
            extra_headers
        )
        return js

    def view_order_revision_detail(self, user_id=None, agency_id=None, agency_group_id=None, campaign_id=None, order_id=None, version=None, revision=None):
        """
        As a buyer, view the detail of one order revision.

        http://developer.mediaocean.com/docs/buyer_orders/Get_order_rev_details_buyer
        """
        if user_id == None:
            user_id = self.user_id
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        if version == None:
            raise PATSException("Order version is required")
        if revision == None:
            raise PATSException("Order revision is required")
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if agency_id == None:
            agency_id = self.agency_id

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Organization-Id': agency_id,
            'X-MO-Agency-Group-Id': agency_group_id,
            'X-MO-User-Id': user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/campaigns/%s/orders/%s/versions/%s/revisions/%s" % (campaign_id, order_id, version, revision),
            extra_headers
        )
        return js

    def get_order_attachment(self, user_id=None, agency_group_id=None, agency_id=None, campaign_id=None, order_id=None, attachment_id=None):
        """
        Get an attachment for an order (including the PDF of the order itself).

        http://developer.mediaocean.com/docs/buyer_orders/Get_order_attachment_buyer
        """
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if agency_id == None:
            agency_id = self.agency_id
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if user_id == None:
            user_id = self.user_id
        if order_id == None:
            raise PATSException("Order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-Agency-Group-Id': agency_group_id,
            'X-MO-Organization-Id': agency_id,
            'X-MO-User-Id': user_id,
            'X-MO-App': 'prisma'
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/campaigns/%s/orders/%s/attachments/%s" % (campaign_id, order_id, attachment_id),
            extra_headers
        )
        return js

    def return_order_revision(self, agency_group_id=None, agency_id=None, user_id=None, campaign_id=None, order_id=None, version=None, revision=None,  seller_email=None, revision_due_date=None, comment=None):
        """
        "Return order revision" which means "Send a message back to the person who sent this revision"

        http://developer.mediaocean.com/docs/buyer_orders/Return_order_rev_buyer
        """
        if agency_id == None:
            agency_id = self.agency_id
        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        # TODO: allow attachments
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Agency-Group-ID': agency_group_id,
            'X-MO-Organization-ID': agency_id,
            'X-MO-User-ID': user_id
        }
        # TODO: allow for list of emails
        data = {
            'revisionDueBy': revision_due_date.strftime("%Y-%m-%d"),
            'comment': comment,
            'emails': [ seller_email ],
            'orderAttachments': [], # leave it blank for now
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/campaigns/%s/orders/%s/versions/%s/revisions/%s/return" % (campaign_id, order_id, version, revision),
            extra_headers,
            json.dumps(data)
        )
        return js

    def request_order_revision(self, agency_group_id=None, agency_id=None, campaign_id=None, order_id=None, version=None, user_id=None, seller_email=None, revision_due_date=None, comment=None):
        """
        "Request order revision" which means "Send a message to the person who received this order"

        http://developer.mediaocean.com/docs/buyer_orders/Request_rev_buyer
        """
        # TODO: allow attachments

        if agency_group_id == None:
            agency_group_id = self.agency_group_id
        if agency_id == None:
            agency_id = self.agency_id
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-App': 'prisma',
            'X-MO-Agency-Group-ID': agency_group_id,
            'X-MO-Organization-ID': agency_id,
            'X-MO-User-ID': user_id
        }
        # TODO: allow for list of emails
        data = {
            'revisionDueBy': revision_due_date.strftime("%Y-%m-%d"),
            'comment': comment,
            'emails': [ seller_email ],
            'orderAttachments': [], # leave it blank for now
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/campaigns/%s/orders/%s/versions/%s/requestRevision" % (campaign_id, order_id, version),
            extra_headers,
            json.dumps(data)
        )
        return js
