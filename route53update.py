#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Update Route53 AWS A record for Dynamic DNS

import sys,os
import subprocess
import re, shlex
from xml.etree.ElementTree import *

# Move to executable directory where dnscur exists
os.chdir(os.path.dirname(sys.argv[0]))

# Add environ for cacert
os.environ['CURL_CA_BUNDLE']='./cacert.pem'

# Temp file
modop_file='_modop.xml'

if len(sys.argv) != 3:
    print "usage: route53update.py host zone-id"
    sys.exit(1)
    
hostname = sys.argv[1]
zoneid = sys.argv[2]
print "target zone %s, host %s" % (zoneid, hostname)
hostname = hostname + '.'

cmd = './dnscurl.pl --keyname my-aws-account -- -H "Content-Type: text/xml; charset=UTF-8" -X GET "https://route53.amazonaws.com/2012-12-12/hostedzone/%s/rrset?name=miyonet.org&type=A" 2>/dev/null' % zoneid
p=subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
result=p.stdout.read()

# Lookup corresponding IP stored in AWS
curip=""
tree=fromstring(result)
NS={'aws':'https://route53.amazonaws.com/doc/2012-12-12/'}
for rrs in tree.findall('.//aws:ResourceRecordSet', namespaces=NS):
    name = rrs.find('.//aws:Name', namespaces=NS)
    if (name.text == hostname):
         curip = rrs.find('.//aws:Value', namespaces=NS).text

# Get IP assigned to my router using chckip.dns.org
# Output format is:
#  <html><head><title>Current IP Check</title></head><body>Current IP Address: 1.2.3.4</body></html>
cmd = 'wget -O - checkip.dyndns.org 2>/dev/null'
p=subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
result = p.stdout.read()

myip=re.findall('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', result)[0]
print "Current IP stored in AWS is %s, my router IP is %s" % (curip, myip)

# Setup xml file template

xmltmpl='''\
<?xml version="1.0" encoding="UTF-8"?>
<ChangeResourceRecordSetsRequest xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ChangeBatch>
      <Comment>
      Migrate existing records to Route 53
      </Comment>
      <Changes>
         <Change>
            <Action>%s</Action>
            <ResourceRecordSet>
               <Name>%s</Name>
               <Type>A</Type>
               <TTL>300</TTL>
               <ResourceRecords>
                  <ResourceRecord>
                     <Value>%s</Value>
                  </ResourceRecord>
               </ResourceRecords>
            </ResourceRecordSet>
         </Change>
      </Changes>
   </ChangeBatch>
</ChangeResourceRecordSetsRequest>
'''

def modop(op, host, zone, ip):
    modop_xml = xmltmpl % (op, host, ip)
           
    f=open(modop_file, 'w')
    f.write(modop_xml)
    f.close()

    cmd = './dnscurl.pl --keyname my-aws-account -- -H "Content-Type: text/xml; charset=UTF-8" -X POST --upload-file %s "https://route53.amazonaws.com/2012-12-12/hostedzone/%s/rrset" >/dev/null 2>&1' % (modop_file, zone)
    os.system(cmd)

modop('DELETE', hostname, zoneid, curip)
modop('CREATE', hostname, zoneid, myip)
