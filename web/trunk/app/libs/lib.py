import urllib2
import socket
import paramiko
from lxml.etree import fromstring


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class StandalonePower(object):
    def __init__(self, host, username, password, timeout=30):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self.cookie = None

    def power_on(self):
        try:
            self.cookie = self.controller_login(self.host, self.username, self.password, self.timeout)
            if self.cookie:
                status = self.controller_status(self.host, self.cookie)
                if status == 'off':
                    self.controller_power(self.host, self.cookie, 'up')
                self.controller_logout(self.host, self.cookie)
        except:
            raise

    def power_off(self):
        try:
            self.cookie = self.controller_login(self.host, self.username, self.password, self.timeout)
            if self.cookie:
                status = self.controller_status(self.host, self.cookie)
                if status == 'on':
                    self.controller_power(self.host, self.cookie, 'down')
                self.controller_logout(self.host, self.cookie)
        except:
            raise

    def power_cycle(self):
        try:
            self.cookie = self.controller_login(self.host, self.username, self.password, self.timeout)
            if self.cookie:
                status = self.controller_status(self.host, self.cookie)
                if status == 'on':
                    self.controller_power(self.host, self.cookie, 'cycle-immediate')
                self.controller_logout(self.host, self.cookie)
        except:
            raise

    def shutdown(self):
        try:
            self.cookie = self.controller_login(self.host, self.username, self.password, self.timeout)
            if self.cookie:
                status = self.controller_status(self.host, self.cookie)
                if status == 'on':
                    self.controller_power(self.host, self.cookie, 'soft-shut-down')
                self.controller_logout(self.host, self.cookie)
        except:
            raise

    @staticmethod
    def controller_login(host=None, username=None, password=None, timeout=30):
        """ Cisco Integrated Management Controller login function using XML API

        xml login output:
        <aaaLogin cookie="" response="yes" outCookie="1480609849/c5f3c85d-429b-129b-802b-a3f9f6ea72f8"
        outRefreshPeriod="600" outPriv="admin" outSessionId="55" outVersion="2.0(8g)"> </aaaLogin>

        xml authentication error:
        <aaaLogin cookie="" response="yes" errorCode="551" invocationResult="unidentified-fail"
        errorDescr="Authentication failed"> </aaaLogin>

        :param str host: cimc ip address
        :param str username: cimc username
        :param str password: cimc password
        :param int timeout: for urlopen connection
        :return: session cookie from xml api
        """
        try:
            data = "<aaaLogin inName='{}' inPassword='{}'></aaaLogin>".format(username, password)
            r = urllib2.Request("http://{}/nuova/".format(host), data=data)
            u = urllib2.urlopen(r, timeout=timeout)
            xml_login = fromstring(u.read())
            if xml_login.attrib.get('errorDescr', None):
                raise ValueError('Error: {}'.format(xml_login.attrib['errorDescr']))
            return xml_login.attrib.get('outCookie', None)
        except urllib2.URLError:
            raise  # re-raise the exception
        except socket.timeout:
            raise urllib2.URLError('Socket timeout after {} seconds'.format(timeout))

    @staticmethod
    def controller_logout(host=None, cookie=None):
        """ Cisco Integrated Management Controller logout function using XML API

        xml logout output:
        <aaaLogout cookie="1480620171/b39d5956-429e-129e-8038-a3f9f6ea72f8"
        response="yes" outStatus="success"></aaaLogout>

        :param str host: cimc ip address
        :param str cookie: session cookie upon login
        :return: None
        """
        try:
            data = "<aaaLogout cookie='{0}' inCookie='{0}'></aaaLogout>".format(cookie)
            r = urllib2.Request("http://{}/nuova/".format(host), data=data)
            urllib2.urlopen(r)
        except urllib2.URLError:
            raise  # re-raise the exception
        except socket.timeout:
            raise urllib2.URLError('Socket timeout')

    @staticmethod
    def controller_status(host=None, cookie=None):
        """ Cisco Integrated Management Controller check current power status function using XML API

        xml status output:
        <configResolveClass cookie="1480620171/b39d5956-429e-129e-8038-a3f9f6ea72f8" response="yes"
        classId="computeRackUnit">\n<outConfigs>\n<computeRackUnit dn="sys/rack-unit-1" adminPower="policy"
        availableMemory="8192" model="UCSC-C22-M3S" memorySpeed="1333" name="UCS C22 M3S" numOfAdaptors="0"
        numOfCores="6" numOfCoresEnabled="6" numOfCpus="1" numOfEthHostIfs="0" numOfFcHostIfs="0" numOfThreads="12"
        operPower="off" originalUuid="76566CE2-5528-4658-8699-D4EBA7B3F671" presence="equipped" serverId="1"
        serial="WZP1739001Z" totalMemory="8192" usrLbl="" uuid="76566CE2-5528-4658-8699-D4EBA7B3F671"
        vendor="Cisco Systems Inc" ></computeRackUnit></outConfigs>\n</configResolveClass>

        :param str host: cimc ip address
        :param str cookie: session cookie upon login
        :return: power status from xml api
        """
        try:
            data = "<configResolveClass cookie='{}' inHierarchical='false' classId='computeRackUnit'/>".format(cookie)
            r = urllib2.Request("http://{}/nuova/".format(host), data=data)
            u = urllib2.urlopen(r)
            etree_parent = fromstring(u.read())
            status = etree_parent.getchildren()[0].getchildren()[0]
            return status.attrib.get('operPower', None)
        except urllib2.URLError:
            raise  # re-raise the exception
        except socket.timeout:
            raise urllib2.URLError('Socket timeout')

    @staticmethod
    def controller_power(host=None, cookie=None, state=None):
        """ Cisco Integrated Management Controller power on or off function using XML API

        xml set power output:
        <configConfMo dn="sys/rack-unit-1" cookie="1480620171/b39d5956-429e-129e-8038-a3f9f6ea72f8" response="yes">\n
        <outConfig>\n<computeRackUnit dn="sys/rack-unit-1" adminPower="policy" availableMemory="8192" model="UCSC-C22-M3S"
        memorySpeed="1333" name="UCS C22 M3S" numOfAdaptors="0" numOfCores="6" numOfCoresEnabled="6" numOfCpus="1"
        numOfEthHostIfs="0" numOfFcHostIfs="0" numOfThreads="12" operPower="on"
        originalUuid="76566CE2-5528-4658-8699-D4EBA7B3F671" presence="equipped" serverId="1" serial="WZP1739001Z"
        totalMemory="8192" usrLbl="" uuid="76566CE2-5528-4658-8699-D4EBA7B3F671" vendor="Cisco Systems Inc"
        status="modified" ></computeRackUnit></outConfig>\n</configConfMo>

        :param str host: cimc ip address
        :param str cookie: session cookie upon login
        :param str state: state input from html form
        :return: None
        """
        try:
            data = "<configConfMo cookie='{}' inHierarchical='false' dn='sys/rack-unit-1'>" \
                   "<inConfig><computeRackUnit adminPower='{}' dn='sys/rack-unit-1'>" \
                   "</computeRackUnit></inConfig></configConfMo>".format(cookie, state)
            r = urllib2.Request("http://{}/nuova/".format(host), data=data)
            urllib2.urlopen(r)
        except urllib2.URLError:
            raise  # re-raise the exception
        except socket.timeout:
            raise urllib2.URLError('Socket timeout')


class VirtualPower(object):
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

    def power_on(self):
        pass

    def power_off(self):
        pass

    def power_cycle(self):
        pass

    def shutdown(self):
        pass

    @staticmethod
    def ssh_connect(host=None, username=None, password=None):
        if not all([host, username, password]):
            raise ValueError('Require inputs for ssh connection')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password)
        return ssh

    @staticmethod
    def ssh_disconnect(ssh):
        if isinstance(ssh, paramiko.SSHClient):
            ssh.close()

    @staticmethod
    def ssh_run_read(ssh, cmd=None):
        if cmd:
            if not isinstance(ssh, paramiko.SSHClient):
                raise ValueError('ssh are not paramiko.SSHClient class')
            stdin, stdout, stderr = ssh.exec_command(cmd)
            return stdout.read(), stderr.read()
        else:
            raise ValueError('Require input command')

    @staticmethod
    def ssh_run_readlines(ssh, cmd=None):
        if cmd:
            if not isinstance(ssh, paramiko.SSHClient):
                raise ValueError('ssh are not paramiko.SSHClient class')
            stdin, stdout, stderr = ssh.exec_command(cmd)
            return stdout.readlines(), stderr.read()
        else:
            raise ValueError('Require input command')
