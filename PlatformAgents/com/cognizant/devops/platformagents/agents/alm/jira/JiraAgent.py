#-------------------------------------------------------------------------------
# Copyright 2017 Cognizant Technology Solutions
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.
#-------------------------------------------------------------------------------
'''
Created on Jun 22, 2016

@author: 463188
'''
from datetime import datetime as dateTime2
import datetime
from dateutil import parser
from com.cognizant.devops.platformagents.core.BaseAgent import BaseAgent

class JiraAgent(BaseAgent):
    def process(self):
        userid = self.config.get("userid", '')
        passwd = self.config.get("passwd", '')
        baseUrl = self.config.get("baseUrl", '')
        startFrom = self.config.get("startFrom", '')
        lastUpdated = self.tracking.get("lastupdated", startFrom)
        responseTemplate = self.getResponseTemplate()
        fields = self.extractFields(responseTemplate)
        jiraIssuesUrl = baseUrl+"?jql=updated>='"+lastUpdated+"' ORDER BY updated ASC&maxResults="+str(self.config.get("dataFetchCount", 1000))+'&fields='+fields
        total = 1
        maxResults = 0
        startAt = 0
        updatetimestamp = None
        sprintField = self.config.get("sprintField", None)
        while (startAt + maxResults) < total:
            data = []
            response = self.getResponse(jiraIssuesUrl+'&startAt='+str(startAt + maxResults), 'GET', userid, passwd, None)
            jiraIssues = response["issues"]
            for issue in jiraIssues:
                parsedIssue = self.parseResponse(responseTemplate, issue)
                if sprintField:
                    sprintDetails = issue.get("fields", {}).get(sprintField, None)
                    if sprintDetails:
                        sprintName = []
                        sprintState = []
                        sprintStartDate = []
                        sprintEndDate = []
                        sprintCompletedDate = []
                        activeSprint = []
                        for sprint in sprintDetails:
                            sprintData = {}
                            sprintDetail = sprint.split("[")[1][:-1]
                            sprintPropertieTokens = sprintDetail.split(",")
                            for propertyToken in sprintPropertieTokens:
                                propertyKeyValToken = propertyToken.split("=")
                                sprintData[propertyKeyValToken[0]] = propertyKeyValToken[1]
                            sprintName.append(sprintData.get('name'))
                            sprintState.append(sprintData.get('state'))
                            sprintStartDate.append(sprintData.get('startDate'))
                            sprintEndDate.append(sprintData.get('endDate'))
                            sprintCompletedDate.append(sprintData.get('completeDate'))
                            if sprintData.get('state') == 'ACTIVE':
                                activeSprint.append(sprintData.get('name'))
                        parsedIssue[0]['activeSprint'] = activeSprint
                        parsedIssue[0]['sprintName'] = sprintName
                        parsedIssue[0]['sprintState'] = sprintState
                        parsedIssue[0]['sprintStartDate'] = sprintStartDate
                        parsedIssue[0]['sprintEndDate'] = sprintEndDate
                        parsedIssue[0]['sprintCompletedDate'] = sprintCompletedDate
                data += parsedIssue
            maxResults = response['maxResults']
            total = response['total']
            startAt = response['startAt']
            if len(jiraIssues) > 0:
                updatetimestamp = jiraIssues[len(jiraIssues) - 1]["fields"]["updated"]
                dt = parser.parse(updatetimestamp)
                fromDateTime = dt + datetime.timedelta(minutes=01)
                fromDateTime = fromDateTime.strftime('%Y-%m-%d %H:%M')
                self.tracking["lastupdated"] = fromDateTime
                self.publishToolsData(data)
                self.updateTrackingJson(self.tracking)
            else:
                break            
    
    def extractFields(self, responseTemplate):
        fieldsJson = responseTemplate.get("fields", None)
        fieldsParam = ''
        if fieldsJson:
            for field in fieldsJson:
                fieldsParam += field + ','
        fieldsParam = fieldsParam[:-1]
        if self.config.get("sprintField", None):
            fieldsParam += ','+ self.config.get("sprintField")
        return fieldsParam
    
    def captureSprintReports(self, userId, password):
        startFromDate = parser.parse(self.config.get("startFrom", ''))
        timeStampFormat = '%Y-%m-%d'
        boardStartAt = 0
        maxResults = 50
        sprintDetails = self.config.get('sprintDetails', None)
        boardApiUrl = sprintDetails.get('boardApiUrl', None)
        sprintReportUrl = sprintDetails.get('sprintReportUrl', None)
        responseTemplate = sprintDetails.get('sprintReportResponseTemplate', None)
        boardTracking = self.tracking.get('boardTracking', None);
        if boardTracking is None:
            boardTracking = {}
            self.tracking['boardTracking'] = boardTracking
        metadata = {
                'labels' : ['METADATA'],
                'dataUpdateSupported' : True,
                'uniqueKey' : 'boardId,sprintId,key'
            }
        while True:
            boardApiRestUrl = boardApiUrl+'?maxResults='+str(maxResults)+'&startAt='+str(boardStartAt)
            boardResponse = self.getResponse(boardApiRestUrl, 'GET', userId, password, None)
            boardValues = boardResponse.get('values', [])
            for board in boardValues:
                boardId = board['id']
                sprintStartAt = 0
                while True:
                    boardSprintRestUrl = boardApiUrl+'/'+str(board['id'])+'/sprint?startAt='+str(sprintStartAt)+'&maxResults='+str(maxResults)
                    try:
                        boardSprintResponse = self.getResponse(boardSprintRestUrl, 'GET', userId, password, None)
                    except Exception as ex:
                        break
                    sprintValues = boardSprintResponse.get('values', [])
                    for sprintValue in sprintValues:
                        sprintCompletedDateStr = sprintValue.get('completeDate', None)
                        if sprintCompletedDateStr:
                            sprintCompletedDateStr = sprintCompletedDateStr.split('T')[0]
                            sprintCompleteDate = parser.parse(sprintCompletedDateStr)
                            if sprintCompleteDate < startFromDate:
                                continue
                        sprintStartTimeStr = sprintValue.get('startDate', None)
                        if sprintStartTimeStr:
                            sprintStartTime = dateTime2.strptime(sprintStartTimeStr.split('T')[0], timeStampFormat)
                        else:
                            continue
                        sprintEndTimeStr = sprintValue.get('endDate', None)
                        if sprintEndTimeStr:
                            sprintEndTime = dateTime2.strptime(sprintEndTimeStr.split('T')[0], timeStampFormat)
                        sprintCompletedTimeStr = sprintValue.get('completeDate', None)
                        if sprintCompletedTimeStr:
                            sprintCompletedTime = dateTime2.strptime(sprintCompletedTimeStr.split('T')[0], timeStampFormat)
                        injectData = {
                                'boardId' : boardId,
                                'boardName' : board['name'],
                                'boardType' : board['type'],
                                'sprintId' : sprintValue['id'],
                                'sprintStartTime' : sprintStartTimeStr,
                                'sprintStartEpochTime' : self.getRemoteDateTime(sprintStartTime).get('epochTime'),
                                'sprintEndTime' : sprintEndTimeStr,
                                'sprintEndEpochTime' : self.getRemoteDateTime(sprintEndTime).get('epochTime'),
                                'sprintCompletedTime' : sprintCompletedTimeStr,
                                'sprintCompletedEpochTime' : self.getRemoteDateTime(sprintCompletedTime).get('epochTime'),
                                'originBoardId' : sprintValue['originBoardId'],
                                'sprintState' : sprintValue['state'],
                                'sprintName' : sprintValue['name'],
                                'almType' : 'sprintReport'
                            }
                        sprintReportRestUrl = sprintReportUrl + '?rapidViewId='+str(boardId)+'&sprintId='+str(injectData['sprintId'])
                        try:
                            sprintReportResponse = self.getResponse(sprintReportRestUrl, 'GET', userId, password, None)
                        except Exception as ex:
                            continue
                        if sprintReportResponse:
                            content = sprintReportResponse.get('contents', None)
                            data = []
                            data += self.addSprintDetails(responseTemplate, content, 'completedIssues', injectData)
                            data += self.addSprintDetails(responseTemplate, content, 'issuesNotCompletedInCurrentSprint', injectData)
                            data += self.addSprintDetails(responseTemplate, content, 'puntedIssues', injectData)
                            data += self.addSprintDetails(responseTemplate, content, 'issuesCompletedInAnotherSprint', injectData)
                            if len(data) > 0:
                                self.publishToolsData(data, metadata)
                                #Need to add tracking
                                #Do not retrieve the sprints which are already completed.
                                #for tracking, store the sprints which are yet to be completed.
                    if boardSprintResponse.get('isLast', True):
                        break
                    else:
                        sprintStartAt = sprintStartAt + maxResults
            if boardResponse.get('isLast', True):
                break
            else:
                boardStartAt = boardStartAt + maxResults
    
    def addSprintDetails(self, responseTemplate, content, sprintIssueRegion, injectData):
        issueKeysAddedDuringSprint = content.get('issueKeysAddedDuringSprint', {})
        issues = content.get(sprintIssueRegion, None)
        parsedIssues = []
        if issues:
            parsedIssues = self.parseResponse(responseTemplate, issues, injectData)
            for issue in parsedIssues:
                issue['addedDuringSprint'] = issueKeysAddedDuringSprint.get(issue['key'], False)
                issue['sprintIssueRegion'] = sprintIssueRegion
        return parsedIssues
        
if __name__ == "__main__":
    JiraAgent()        
