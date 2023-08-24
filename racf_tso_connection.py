import sys, time
from zowe.zos_tso_for_zowe_sdk import Tso


class RacfTsoConnection:
    """
    A class to manage TSO sessions and executions.
    """

    MAX_NUMBER_OF_TSO_CLEAR_SENT = 6

    def __init__(self, host_url: str, user: str, password: str, ssl_verification = False, tso_session = ''):
        """
        Constructs a new instance o TSO class using RACF connection info and credentials.
        
        Parameters:
            host_url: str
                RACF host url
            user: str
                User responsible to perform all the executions on RACF
            password: str
                Password for user 
            ssl_verification: boolean, Optional
                Enable ssl verification. (default is False)
            tso_session: str
                Value defined in case to reuse a session, if empty a new tso session must be created. (default is empty)                
            
        """
        connection = {"host_url": host_url, "user": user, "password": password, "ssl_verification": ssl_verification}
        self.my_tso = Tso(connection)

        self.tso_session = tso_session

        self.proc = "IZUFPROC"
        self.chset = "697"
        self.cpage = "1047"
        self.rows = "204"
        self.cols = "160"
        self.rsize = "4096"
        self.acct = "63606"

    def get_current_tso_session(self,):
        """Create a new TSO session if the session is not defined or if the session is not valid. 
           This method try five times to define a new tso session.
        
            Returns
            -------
            new_tso_session: str
                String that contains a new and valid tso session number
        """
        success = False
        max_retries = 5
        count = 0
        tso_result = ''

        while success == False:
            try:
                ping = ''
                count = count + 1
                if (self.tso_session == "" or self.tso_session == None):
                    ping = ''
                else:
                    ping = self.my_tso.ping_tso_session(self.tso_session)

                if ping.lower() != "ping successful":
                    self.tso_session = self.my_tso.start_tso_session(proc=self.proc, chset=self.chset, cpage=self.cpage, rows=self.rows, cols=self.cols, rsize=self.rsize, acct=self.acct)
                    success = True
                    continue
                elif ping.lower() == 'ping successful':
                    success = True
                    continue
            except:
                time.sleep(5)
            finally:
                if count >= max_retries:
                    self.tso_session = ''
                    break

        return self.tso_session


    def end_tso_session(self):
        """Ends the current TSO session.
            
           Returns
           -------
           None
        """
        if self.tso_session != '' and self.tso_session != None:
            tso_session_temp = self.tso_session
            self.tso_session = ''
            self.my_tso.end_tso_session(tso_session_temp)


    def execute_tso_command(self, command):
        """ 
        Execute a TSO command using the current tso session, 
        and returns the status of the execution and the all TSO command output. 

        Parameters
        ----------
        command : str
            TSO command that needs to be executed

        Returns
        ----------
        success,answer: tuple
            success (boolean) contains the execution status,  true = success, false = failed   
            answer (list[str]) contains all the output for TSO command executed
            
        """
        success = False
        r = int(0)
        tso_clear = False

        while success == False:
            tso_json = ''
            number_of_tso_clear_sent = 0
            while number_of_tso_clear_sent < self.MAX_NUMBER_OF_TSO_CLEAR_SENT:
                tso_json = self.my_tso.send_tso_message(self.tso_session, '')
                tso_ready_message = self.my_tso.retrieve_tso_messages(tso_json)

                if tso_ready_message[0].strip() == 'READY':
                    tso_clear = True
                    break
                number_of_tso_clear_sent = number_of_tso_clear_sent + 1

            if not tso_clear:
                self.end_tso_session()
                self.tso_session = self.get_current_tso_session()

            tso_json = ''
            tso_json = self.my_tso.send_tso_message(self.tso_session, command)
            tso_message = self.my_tso.retrieve_tso_messages(tso_json)

            if tso_message[len(tso_message) - 1].strip() != 'READY':
                tso_clear = False
                while tso_clear == False:
                    tso_json = ''
                    tso_json = self.my_tso.send_tso_message(self.tso_session, '')
                    tso_message_next = self.my_tso.retrieve_tso_messages(tso_json)
                    tso_message = tso_message + tso_message_next

                    if tso_message[len(tso_message) - 1].strip() != 'READY':
                        tso_clear = True
            success = True

        answer = []
        for m in tso_message:
            if m.strip() != 'READY':
                answer.append(m.rstrip())

        self.end_tso_session()

        return success,answer
