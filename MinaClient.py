#!/usr/bin/python3

import random
import requests
import time
import json
import asyncio
import websockets
from websockets import client as wsClient
import logging
from enum import Enum

class CurrencyFormat(Enum):
  """An Enum representing different formats of Currency in mina.

  Constants:
      WHOLE - represents whole mina (1 whole mina == 10^9 nanominas)
      NANO - represents the atomic unit of mina
  """
  WHOLE = 1
  NANO = 2

class CurrencyUnderflow(Exception):
  pass

class Currency():
  """A convenience wrapper around interacting with mina currency values.

  This class supports performing math on Currency values of differing formats.
  Currency instances can be added or subtracted. Currency instances can also be
  scaled through multiplication (either against another Currency instance or a
  int scalar).
  """

  @classmethod
  def __nanominas_from_int(_cls, n):
    return n * 1000000000

  @classmethod
  def __nanominas_from_string(_cls, s):
    segments = s.split('.')
    if len(segments) == 1:
      return int(segments[0])
    elif len(segments) == 2:
      [l, r] = segments
      if len(r) <= 9:
        return int(l + r + ('0' * (9 - len(r))))
      else:
        raise Exception('invalid mina currency format: %s' % s)

  @classmethod
  def random(_cls, lower_bound, upper_bound):
    """Generates a random Currency instance between a provided lower_bound and upper_bound

    Arguments:
        lower_bound {Currency} -- A Currency instance representing the lower bound for the randomly generated value
        upper_bound {Currency} -- A Currency instance representing the upper bound for the randomly generated value

    Returns:
        Currency - A randomly generated Currency instance between the lower_bound and upper_bound
    """
    if not (isinstance(lower_bound, Currency) and isinstance(upper_bound, Currency)):
      raise Exception('invalid call to Currency.random: lower and upper bound must be instances of Currency')
    if not upper_bound.nanominas() >= lower_bound.nanominas():
      raise Exception('invalid call to Currency.random: upper_bound is not greater than lower_bound')
    if lower_bound == upper_bound:
      return lower_bound
    bound_range = upper_bound.nanominas() - lower_bound.nanominas()
    delta = random.randint(0, bound_range)
    return lower_bound + Currency(delta, format=CurrencyFormat.NANO)

  def __init__(self, value, format=CurrencyFormat.WHOLE):
    """Constructs a new Currency instance. Values of different CurrencyFormats may be passed in to construct the instance.

    Arguments:
        value {int|float|string} - The value to construct the Currency instance from
        format {CurrencyFormat} - The representation format of the value

    Return:
        Currency - The newly constructed Currency instance

    In the case of format=CurrencyFormat.WHOLE, then it is interpreted as value * 10^9 nanominas.
    In the case of format=CurrencyFormat.NANO, value is only allowed to be an int, as there can be no decimal point for nanominas.
    """
    if format == CurrencyFormat.WHOLE:
      if isinstance(value, int):
        self.__nanominas = Currency.__nanominas_from_int(value)
      elif isinstance(value, float):
        self.__nanominas = Currency.__nanominas_from_string(str(value))
      elif isinstance(value, str):
        self.__nanominas = Currency.__nanominas_from_string(value)
      else:
        raise Exception('cannot construct whole Currency from %s' % type(value))
    elif format == CurrencyFormat.NANO:
      if isinstance(value, int):
        self.__nanominas = value
      else:
        raise Exception('cannot construct nano Currency from %s' % type(value))
    else:
      raise Exception('invalid Currency format %s' % format)

  def decimal_format(self):
    """Computes the string decimal format representation of a Currency instance.

    Return:
        str - The decimal format representation of the Currency instance
    """
    s = str(self.__nanominas)
    if len(s) > 9:
      return s[:-9] + '.' + s[-9:]
    else:
      return '0.' + ('0' * (9 - len(s))) + s

  def nanominas(self):
    """Accesses the raw nanominas representation of a Currency instance.

    Return:
        int - The nanominas of the Currency instance represented as an integer
    """
    return self.__nanominas

  def __str__(self):
    return self.decimal_format()

  def __repr__(self):
    return 'Currency(%s)' % self.decimal_format()

  def __add__(self, other):
    if isinstance(other, Currency):
      return Currency(self.nanominas() + other.nanominas(), format=CurrencyFormat.NANO)
    else:
      raise Exception('cannot add Currency and %s' % type(other))

  def __sub__(self, other):
    if isinstance(other, Currency):
      new_value = self.nanominas() - other.nanominas()
      if new_value >= 0:
        return Currency(new_value, format=CurrencyFormat.NANO)
      else:
        raise CurrencyUnderflow()
    else:
      raise Exception('cannot subtract Currency and %s' % type(other))

  def __mul__(self, other):
    if isinstance(other, int):
      return Currency(self.nanominas() * other, format=CurrencyFormat.NANO)
    elif isinstance(other, Currency):
      return Currency(self.nanominas() * other.nanominas(), format=CurrencyFormat.NANO)
    else:
      raise Exception('cannot multiply Currency and %s' % type(other))

class Client():
  # Implements a GraphQL Client for the Mina Daemon

  def __init__(
      self,
      graphql_protocol: str = "http",
      websocket_protocol: str = "ws",
      graphql_host: str = "localhost",
      graphql_path: str = "/graphql",
      graphql_port: int = 3085,
  ):
    self.endpoint = "{}://{}:{}{}".format(graphql_protocol, graphql_host, graphql_port, graphql_path)
    self.websocket_endpoint = "{}://{}:{}{}".format(websocket_protocol, graphql_host, graphql_port, graphql_path)
    self.logger = logging.getLogger(__name__)

  def _send_query(self, query: str, variables: dict = {}) -> dict:
    """Sends a query to the Mina Daemon's GraphQL Endpoint
    
    Arguments:
        query {str} -- A GraphQL Query
    
    Keyword Arguments:
        variables {dict} -- Optional Variables for the query (default: {{}})
    
    Returns:
        dict -- A Response object from the GraphQL Server.
    """
    return self._graphql_request(query, variables)

  def _send_mutation(self, query: str, variables: dict = {}) -> dict:
    """Sends a mutation to the Mina Daemon's GraphQL Endpoint.
    
    Arguments:
        query {str} -- A GraphQL Mutation
    
    Keyword Arguments:
        variables {dict} -- Variables for the mutation (default: {{}})
    
    Returns:
        dict -- A Response object from the GraphQL Server.
    """
    return self._graphql_request(query, variables)
  
  def _graphql_request(self, query: str, variables: dict = {}):
    """GraphQL queries all look alike, this is a generic function to facilitate a GraphQL Request.
    
    Arguments:
        query {str} -- A GraphQL Query
    
    Keyword Arguments:
        variables {dict} -- Optional Variables for the GraphQL Query (default: {{}})
    
    Raises:
        Exception: Raises an exception if the response is anything other than 200.
    
    Returns:
        dict -- Returns the JSON Response as a Dict.
    """
    # Strip all the whitespace and replace with spaces
    query = " ".join(query.split())
    payload = {'query': query}
    if variables:
      payload = { **payload, 'variables': variables }

    headers = {
      "Accept": "application/json"
    }
    self.logger.debug("Sending a Query: {}".format(payload))
    response = requests.post(self.endpoint, json=payload, headers=headers)
    resp_json = response.json()
    if response.status_code == 200 and "errors" not in resp_json:
      self.logger.debug("Got a Response: {}".format(response.json()))
      return resp_json
    else:
      print(response.text)
      raise Exception(
          "Query failed -- returned code {}. {} -> {}".format(response.status_code, query, response.json()))
  
  async def _graphql_subscription(self, query: str, variables: dict = {}, callback = None): 
    hello_message = {"type": "connection_init", "payload": {}}

    # Strip all the whitespace and replace with spaces
    query = " ".join(query.split())
    payload = {'query': query}
    if variables:
      payload = { **payload, 'variables': variables }
    
    query_message = {"id": "1", "type": "start", "payload": payload}
    self.logger.info("Listening to GraphQL Subscription...")
    
    uri = self.websocket_endpoint
    self.logger.info(uri)
    async with wsClient.connect(uri, ping_timeout=None) as websocket:
      # Set up Websocket Connection
      self.logger.debug("WEBSOCKET -- Sending Hello Message: {}".format(hello_message))
      await websocket.send(json.dumps(hello_message))
      resp = await websocket.recv()
      self.logger.debug("WEBSOCKET -- Recieved Response {}".format(resp))
      self.logger.debug("WEBSOCKET -- Sending Subscribe Query: {}".format(query_message))
      await websocket.send(json.dumps(query_message))

      # Wait for and iterate over messages in the connection
      async for message in websocket:
        self.logger.debug("Recieved a message from a Subscription: {}".format(message))
        if callback: 
          callback(message)
        else:
          print(message)
  
  def get_daemon_status(self) -> dict:
    """Gets the status of the currently configured Mina Daemon.
    
    Returns:
         dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    query {
      daemonStatus {
        numAccounts
        blockchainLength
        highestBlockLengthReceived
        uptimeSecs
        ledgerMerkleRoot
        stateHash
        commitId
        userCommandsSent
        snarkWorker
        snarkWorkFee
        syncStatus
        consensusTimeBestTip
        consensusTimeNow
        consensusMechanism
        confDir
        commitId
        consensusConfiguration {
          delta
          k
          slotsPerEpoch
          slotDuration
          epochDuration
          acceptableNetworkDelay
        }
      }
    }
    '''
    res = self._send_query(query)
    return res['data']

  def get_daemon_version(self) -> dict:
    """Gets the version of the currently configured Mina Daemon.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    {
        version
    }
    '''
    res = self._send_query(query)
    return res["data"]

  def get_wallets(self) -> dict:
    """Gets the wallets that are currently installed in the Mina Daemon.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    {
      ownedWallets {
        publicKey
        balance {
          total
        }
      }
    }
    '''
    res = self._send_query(query)
    return res["data"]

  def get_wallet(self, pk: str) -> dict:
    """Gets the wallet for the specified Public Key.
    
    Arguments:
        pk {str} -- A Public Key corresponding to a currently installed wallet.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    query($publicKey:PublicKey!){
      wallet(publicKey:$publicKey) {
        publicKey
    		balance {
    		  total
    		  unknown
    		}
        nonce
        receiptChainHash
        delegate
        votingFor
        stakingActive
        privateKeyPath
      }
    }
    '''
    variables = {
      "publicKey": pk
    }
    res = self._send_query(query, variables)
    return res["data"]

  def create_wallet(self, password: str) -> dict:
    """Creates a new Wallet.
    
    Arguments:
        password {str} -- A password for the wallet to unlock.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    mutation ($password: String!) {
      createAccount(input: {password: $password}) {
        publicKey
      }
    }
    '''
    variables = {
      "password": password
    }
    res = self._send_query(query, variables)
    return res["data"]

  def unlock_wallet(self, pk: str, password: str) -> dict:
    """Unlocks the wallet for the specified Public Key.
    
    Arguments:
        pk {str} -- A Public Key corresponding to a currently installed wallet.
        password {str} -- A password for the wallet to unlock.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    mutation ($publicKey: PublicKey!, $password: String!) {
      unlockWallet(input: {publicKey: $publicKey, password: $password}) {
        account {
          balance {
            total
          }
        }
      }
    }
    '''
    variables = {
      "publicKey": pk,
      "password": password
    }
    res = self._send_query(query, variables)
    return res["data"]

  def get_blocks(self) -> dict:
    """Gets the blocks known to the Mina Daemon. 
    Mostly useful for Archive nodes. 
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    {
      blocks{
        nodes {
          creatorAccount
          stateHash
          protocolState {
            previousStateHash
            blockchainState{
              date
              snarkedLedgerHash
              stagedLedgerHash
            }
          }
          transactions {
            userCommands{
              id
              isDelegation
              nonce
              from
              to
              amount
              fee
              memo
            }
            feeTransfer {
              recipient
              fee
            }
            coinbase
          }
          snarkJobs {
            prover
            fee
            workIds
          }
        }
        pageInfo {
          hasNextPage
          hasPreviousPage
          firstCursor
          lastCursor
        }
      }
    }
    '''
    res = self._send_query(query)
    return res["data"]    

  def get_current_snark_worker(self) -> dict:
    """Gets the currently configured SNARK Worker from the Mina Daemon. 
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    {
      currentSnarkWorker{
        key
        fee
      }
    }
    '''
    res = self._send_query(query)
    return res["data"]

  def get_sync_status(self) -> dict:
    """Gets the Sync Status of the Mina Daemon.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    {
      syncStatus
    }
    '''
    res = self._send_query(query)
    return res["data"]

  def get_peers(self) -> dict:
    """Gets the peers connected to the Mina Daemon
    
    Returns:
        dict -- Returns the data field of the JSON Response as a Dict
    """
    query = '''
    daemonStatus {
      peers {
        host
        libp2pPort
        peerId
      }
    }
    '''
    res = self._send_query(query)
    return res["data"]
    
  def set_current_snark_worker(self, worker_pk: str, fee: str) -> dict: 
    """Set the current SNARK Worker preference. 
    
    Arguments:
        worker_pk {str} -- The public key corresponding to the desired SNARK Worker
        fee {str} -- The desired SNARK Work fee
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict
    """
    query = '''
    mutation($worker_pk:PublicKey!, $fee:UInt64!){
      setSnarkWorker(input: {publicKey:$worker_pk}) {
        lastSnarkWorker
      }
      setSnarkWorkFee(input: {fee:$fee})
    }'''
    variables = {
      "worker_pk": worker_pk,
      "fee": fee
    }
    res = self._send_mutation(query, variables)
    return res["data"]

  def send_payment(self, to_pk: str, from_pk: str, amount: Currency, fee: Currency, memo: str) -> dict:
    """Send a payment from the specified wallet to the specified target wallet. 
    
    Arguments:
        to_pk {PublicKey} -- The target wallet where funds should be sent
        from_pk {PublicKey} -- The installed wallet which will finance the payment
        amount {UInt64} -- Tha amount of Mina to send
        fee {UInt64} -- The transaction fee that will be attached to the payment
        memo {str} -- A memo to attach to the payment
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict
    """
    query = '''
    mutation($from:PublicKey!, $to:PublicKey!, $amount:UInt64!, $fee:UInt64!, $memo:String){
      sendPayment(input: {
        from:$from,
        to:$to,
        amount:$amount,
        fee:$fee,
        memo:$memo
      }) {
        payment {
          id,
          isDelegation,
          nonce,
          from,
          to,
          amount,
          fee,
          memo
        }
      }
    }
    '''
    variables = {
      "from": from_pk,
      "to": to_pk,
      "amount": amount.nanominas(),
      "fee": fee.nanominas(),
      "memo": memo
    }
    res = self._send_mutation(query, variables)
    return res["data"]

  def get_pooled_payments(self, pk: str) -> dict:
    """Get the current transactions in the payments pool 
    
    Arguments:
        pk {str} -- The public key corresponding to the installed wallet that will be queried 
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict
    """
    query = '''
    query ($publicKey:String!){
      pooledUserCommands(publicKey:$publicKey) {
        id,
        isDelegation,
        nonce,
        from,
        to,
        amount,
        fee,
        memo
      }
    }
    '''
    variables = {
      "publicKey": pk
    }
    res = self._send_query(query, variables)
    return res["data"]

  def get_transaction_status(self, payment_id: str) -> dict:
    """Get the transaction status for the specified Payment Id.
    
    Arguments:
        payment_id {str} -- A Payment Id corresponding to a UserCommand.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    query($paymentId:ID!){
      transactionStatus(payment:$paymentId)
    }
    '''
    variables = {
      "paymentId": payment_id
    }
    res = self._send_query(query, variables)
    return res["data"]    

  async def listen_sync_update(self, callback):
    """Creates a subscription for Network Sync Updates
    """
    query = '''
    subscription{
      newSyncUpdate 
    }
    '''
    await self._graphql_subscription(query, {}, callback)
    
  async def listen_block_confirmations(self, callback):
    """Creates a subscription for Block Confirmations
    Calls callback when a new block is recieved. 
    """
    query = '''
    subscription{
      blockConfirmation {
        stateHash
        numConfirmations
      }
    }
    '''
    await self._graphql_subscription(query, {}, callback)

  async def listen_new_blocks(self, callback):
    """Creates a subscription for new blocks, calls `callback` each time the subscription fires.
    
    Arguments:
        callback(block) {coroutine} -- This coroutine is executed with the new block as an argument each time the subscription fires
    """
    query = '''
    subscription(){
      newBlock(){
        creatorAccount {
          publicKey
          balance {
            liquid
            locked
            total
          }
        }
        stateHash
        protocolState {
          previousStateHash
          blockchainState {
            date
            snarkedLedgerHash
            stagedLedgerHash
          }
          consensusState {
            blockHeight
            epochCount
            minWindowDensity
            lastVrfOutput
            totalCurrency
            hasAncestorInSameCheckpointWindow
            slot
            slotSinceGenesis
            epoch
          }
        },
        transactions {
          userCommands {
            hash
            kind
            nonce
            feePayer {
              publicKey
              balance {
                liquid
                locked
                total
              }
            }
            source {
              publicKey
              balance {
                liquid
                locked
                total
              }
            }
            receiver {
              publicKey
              balance {
                liquid
                locked
                total
              }
            }
            amount
            fee
            memo
            token
            feeToken
            failureReason
          }
          feeTransfer {
            recipient
            fee
          }
          coinbase
          coinbaseReceiverAccount {
              publicKey
              balance {
                liquid
                locked
                total
              }
            }
        },
        snarkJobs {
          prover
          fee
          workIds
        }
      }
    }
    '''
    variables = {
    }
    await self._graphql_subscription(query, variables, callback)


  async def listen_chain_reorganization(self, callback):
    """Creates a subscription for reorganization.
    
    Arguments:
        callback(block) {coroutine} -- This coroutine is executed with the new block as an argument each time the subscription fires
    """
    query = '''
    subscription(){
      ChainReorganization
    }
    '''
    variables = {
    }
    await self._graphql_subscription(query, variables, callback)
  
  def get_best_chain(self, num_blocks ) -> dict:
    """Gets the best chain for the daemon.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    {
    bestChain(maxLength: %s) {
        stateHash
        protocolState {
        consensusState {
            blockHeight
          }
        previousStateHash
        }
      }
    }
    ''' % num_blocks
    res = self._send_query(query)
    return res["data"]


  def get_peers(self ) -> dict:
    """Gets the Peers List.
    
    Returns:
        dict -- Returns the "data" field of the JSON Response as a Dict.
    """
    query = '''
    {
      getPeers {
        host
        libp2pPort
        peerId
      }
    }
    '''
    res = self._send_query(query)
    return res["data"]
