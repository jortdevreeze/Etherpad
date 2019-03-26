# -*- coding: utf-8 -*-
"""
Created on Tue Mar 26 11:59:58 2019

@author: jdevreeze
"""
from datetime import datetime
from distutils.version import StrictVersion

import bs4 as bs
import requests

import inspect
import re

class Etherpad:
    """
    This class extracts Etherpad data
    """  
    
    _ignore = True
    _print_errors = True
    
    _base = None
    _apikey = None
    
    _version = '1.2.12'
    
    _log = []
    
    def __init__(self, url, apikey, version=None, ignore=True):
        """
        Initialize the Etherpad class.   
        
        Args:
            url: The base url for the API.
            apikey: The secret key to access the API.
            version: Change the version of Etherpad (Note some methods might not work).
            ignore: Set to False to raise exeptions, which is helpfull for debugging (default True).
        
        Returns:
            False in case of an error.
        Raises:
            ValueError: A valid url must be specified.
            ValueError: A valid API key must be specified.
        """
        
        if ignore is False:
            self._ignore = False
            
        if type(url) is not str:
            self.__error(self.__line_no(), 'A valid url must be specified.', None)
            return False
        else:
            self._base = url
        
        if type(apikey) is not str:
            self.__error(self.__line_no(), 'A valid API key must be specified.', None)
            return False
        else:
            self._apikey = apikey  
            
        if type(version) is str:
            self._version = version        

    def unique_contributions(self, pad, authors):
        """
        Extract all unique_contributions from a saved etherpad pad.
        
        Args:
            pad: The pad name.
            auhors: The author names for which the contributions need to be extracted.

        Returns:
            A list with all text added by each author and a list of all text deleted by each author.
        
        Raises:
            ValueError: Etherpad API version 1.2.7 or later is required.
            ValueError: An error message from the etherpad API.
        """
        
        if StrictVersion(self._version) < StrictVersion('1.2.7'):
            self.__error(self.__line_no(), 'Etherpad API version 1.2.7 or later is required, you have ,', self._version, '.', None)
            return False
        
        params = {
            'padID' : pad,
            'startRev' : 1 
        }
        
        # Extract the data for this method
        data = self._request('createDiffHTML', params)
        
        if data['code'] is not 0:
            self.__error(self.__line_no(), data['message'], None)
            return False
        
        content = data['data']['html']
    
        # Remove escape character from the document
        content = re.sub('\"', '"', content)
        content = re.sub('\n', '', content)
        content = re.sub('\t', '', content)
        content = re.sub('\r', '', content)
        
        soup = bs.BeautifulSoup(content, 'html.parser')
        
        # Remove all styles from the content    
        elements = content.findAll('style')
        for element in elements:
            element.replace_with('')

        added = deleted = []
        
        for author in authors:

            c = []
            d = []
            
            edits = soup.find_all('span', class_='author{}'.format(author))
            
            for edit in edits:
                if edit.find('span') is not None:
                    d.append(str(edit.span.string))
                else:
                    c.append(str(edit.string))
            
            added.append(c)
            deleted.append(d)
            
        return added, deleted
    
    def unique_authors(self, pad):
        """
        Extract all unique authors from a saved etherpad pad.
        
        Args:
            pad: The pad name.

        Returns:
            A list with all authors.
        
        Raises:
            ValueError: Etherpad API version 1 or later is required.
            ValueError: An error message from the etherpad API.
        """
        
        if StrictVersion(self._version) < StrictVersion('1'):
            self.__error(self.__line_no(), 'Etherpad API version 1 or later is required, you have ,', self._version, '.', None)
            return False
        
        params = {
            'padID' : pad
        }
        
        # Extract the data for this method
        data = self._request('listAuthorsOfPad', params)
        
        if data['code'] is not 0:
            self.__error(self.__line_no(), data['message'], None)
            return False
        
        return data['data']['authorIDs']

            
    def _request(self, method, params):
        """
        Internal method which extracts information from the Etherpad API.    
        
        Args:
            method: A string with an API supported method name.
            params: A dict with the Etherpad API paramaters for the specified method.
        
        Returns:
            A json object.
        
        Raises:
            ValueError: An unexpected error occured while connecting to Wikipedia.
        """ 
        
        url = 'pad.{}/api/{}/{}'.format(self._base, self._version, method)        
        params = { 'apikey' : self._apikey }.update(params)
        
        resp = requests.get(url, params)
        
        if resp.status_code != requests.codes.ok:
             raise ValueError("An unexpected error occured while connecting to Etherpad API (Status code: ", resp.status_code, ").")
        
        return resp.json()
    
    def __line_no(self):
        """
        Internal method to get the current line number.
        
        Returns:
            An integer with the current line number.
        """
        
        return inspect.currentframe().f_back.f_lineno
        
    def __error(self, line, error, etype):
        """
        Internal method to handle errors.    
        
        Args:
            line: An integer with the current line number
            error: A string with the error message.
            etype: A string with the error type
        """

        if self._print_errors is True:
            print('Line:', line, '-', error)
            
        self._log.append((datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S%Z'), line, error, etype))
        
        if self._ignore is False:
            raise ValueError(error)

