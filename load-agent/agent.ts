import {
  AnonCredsModule, 
  LegacyIndyCredentialFormatService,
  LegacyIndyProofFormatService,
  V1CredentialProtocol, 
  V1ProofProtocol
} from '@aries-framework/anoncreds';

import {
  IndySdkIndyDidRegistrar, 
  IndySdkSovDidResolver, 
  IndySdkIndyDidResolver
} from '@aries-framework/indy-sdk'

import { AskarModule } from '@aries-framework/askar'
import { ariesAskar } from '@hyperledger/aries-askar-nodejs'

import {
  Agent, 
  BasicMessageEventTypes,
  ConnectionEventTypes,
  ConsoleLogger, 
  CredentialEventTypes,
  CredentialsModule, 
  CredentialState,
  DidCommMimeType, 
  DidExchangeState,
  DidRepository,
  DidsModule, 
  HttpOutboundTransport,
  LogLevel, 
  MediationRecipientModule, 
  MediatorPickupStrategy, 
  ProofEventTypes,
  ProofsModule, 
  ProofState,
  TransportEventTypes,
  TrustPingEventTypes,
  V2CredentialProtocol, 
  V2ProofProtocol, 
  WsOutboundTransport
} from '@aries-framework/core';

import { 
  agentDependencies, 
  HttpInboundTransport 
} from '@aries-framework/node';

import { AnonCredsRsModule } from '@aries-framework/anoncreds-rs'
import { anoncreds } from '@hyperledger/anoncreds-nodejs'
import { IndyVdrAnonCredsRegistry, IndyVdrModule } from '@aries-framework/indy-vdr'
import { indyVdr } from '@hyperledger/indy-vdr-nodejs'

var config = require('./config.js')

var deferred = require('deferred')
var process = require('process')

const characters =
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
const legacyIndyCredentialFormat = new LegacyIndyCredentialFormatService()
const legacyIndyProofFormat = new LegacyIndyProofFormatService()

function generateString(length) {
  let result = ''
  const charactersLength = characters.length
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength))
  }

  return result
}

const initializeAgent = async (withMediation, port, agentConfig = null) => {
  // Simple agent configuration. This sets some basic fields like the wallet
  // configuration and the label. It also sets the mediator invitation url,
  // because this is most likely required in a mobile environment.

  let mediation_url = config.mediation_url
  let endpoints = ['http://' + config.agent_ip + ':' + port]

  if (!agentConfig || agentConfig === null || agentConfig.length === 0) {
    agentConfig = {
      label: generateString(14),
      walletConfig: {
        id: generateString(32),
        key: generateString(32),
      },
      autoAcceptConnections: true,
      endpoints: endpoints,

      autoAcceptInvitation: true,
      // logger: new ConsoleLogger(LogLevel.trace),
      didCommMimeType: DidCommMimeType.V0,
    }
  }

  let modules = {
    askar: new AskarModule({
      ariesAskar,
    }),
    mediationRecipient: new MediationRecipientModule({
      mediatorInvitationUrl: mediation_url,
//      mediatorPickupStrategy: MediatorPickupStrategy.PickUpV2,
      mediatorPickupStrategy: MediatorPickupStrategy.Implicit,
    }),
    anoncredsRs: new AnonCredsRsModule({
      anoncreds,
    }),
    indyVdr: new IndyVdrModule({
      indyVdr,
      networks: [config.ledger]
    }),
    anoncreds: new AnonCredsModule({
      registries: [new IndyVdrAnonCredsRegistry()],
    }),
    proofs: new ProofsModule({
      proofProtocols: [
        new V1ProofProtocol({
          indyProofFormat: legacyIndyProofFormat,
        }),
        new V2ProofProtocol({
          proofFormats: [legacyIndyProofFormat],
        }),
      ],
    }),
    credentials: new CredentialsModule({
      credentialProtocols: [
        new V1CredentialProtocol({
          indyCredentialFormat: legacyIndyCredentialFormat,
        }),
        new V2CredentialProtocol({
          credentialFormats: [legacyIndyCredentialFormat],
        }),
      ],
    }),
    dids: new DidsModule({
      registrars: [new IndySdkIndyDidRegistrar()],
      resolvers: [new IndySdkSovDidResolver(), new IndySdkIndyDidResolver()],
    })
  }

  // configure mediator or endpoints
  if (withMediation) {
    delete agentConfig['endpoints']
  } else {
    delete modules['mediationRecipient']
  }

  // A new instance of an agent is created here
  const agent = new Agent({
    config: agentConfig,
    dependencies: agentDependencies,
    modules: modules
  })

  // Register a simple `WebSocket` outbound transport
  agent.registerOutboundTransport(new WsOutboundTransport())

  // Register a simple `Http` outbound transport
  agent.registerOutboundTransport(new HttpOutboundTransport())

  if (withMediation) {
    // wait for medation to be configured
    let timeout = config.verified_timeout_seconds * 1000

    const TimeDelay = new Promise((resolve, reject) => {
      setTimeout(resolve, timeout, false)
    })

    var def = deferred()

    var onConnectedMediation = async (event) => {
      let mediatorConnection = null
      let interval = 100; 
      for (let i = 0; i < (timeout - interval); i++)
      {
        // OutboundWebSocketOpenedEvent occurs before mediation is finalized, so we want to check
        // for the default mediation connection until it is not null or we hit a timeout
        // we sleep a small amount between requests just to be kind to our CPU. 
        await new Promise(r => setTimeout(r, interval))
        mediatorConnection = await agent.mediationRecipient.findDefaultMediatorConnection()
        if (mediatorConnection != null) {
          break;
        }
      }
      if (event.payload.connectionId === mediatorConnection?.id) {
        def.resolve(true)
        // we no longer need to listen to the event
        agent.events.off(
          TransportEventTypes.OutboundWebSocketOpenedEvent,
          onConnectedMediation
        )
      }
    }

    agent.events.on(
      TransportEventTypes.OutboundWebSocketOpenedEvent,
      onConnectedMediation
    )

    // Initialize the agent
    await agent.initialize()

    // wait for ws to be configured
    let value = await Promise.race([TimeDelay, def.promise])

    if (!value) {
      // we no longer need to listen to the event in case of failure
      agent.events.off(
        TransportEventTypes.OutboundWebSocketOpenedEvent,
        onConnectedMediation
      )
      throw 'Mediator timeout!'
    }
  } else {
    agent.registerInboundTransport(
      new HttpInboundTransport({ port: port })
    )
    await agent.initialize()
  }

  return [agent, agentConfig]
}

const pingMediator = async (agent) => {
  // Find mediator

  // wait for the ping
  let timeout = config.verified_timeout_seconds * 1000

  const TimeDelay = new Promise((resolve, reject) => {
    setTimeout(resolve, timeout, false)
  })

  var def = deferred()

  var onPingResponse = async (event) => {
    const mediatorConnection =
      await agent.mediationRecipient.findDefaultMediatorConnection()
    if (event.payload.connectionRecord.id === mediatorConnection?.id) {
      // we no longer need to listen to the event
      agent.events.off(
        TrustPingEventTypes.TrustPingResponseReceivedEvent,
        onPingResponse
      )

      def.resolve(true)
    }
  }

  agent.events.on(
    TrustPingEventTypes.TrustPingResponseReceivedEvent,
    onPingResponse
  )

  let mediatorConnection =
    await agent.mediationRecipient.findDefaultMediatorConnection()

  if (mediatorConnection) {
    //await agent.connections.acceptResponse(mediatorConnection.id)
    await agent.connections.sendPing(mediatorConnection.id, {})
  }

  // wait for ping repsonse
  let value = await Promise.race([TimeDelay, def.promise])

  if (!value) {
    // we no longer need to listen to the event in case of failure
    agent.events.off(
      TrustPingEventTypes.TrustPingResponseReceivedEvent,
      onPingResponse
    )
    throw 'Mediator timeout!'
  }
}

let deleteOobRecordById = async (agent, id) => {
  await agent.oob.deleteById(id);
};

let receiveInvitation = async (agent, invitationUrl) => {
  // wait for the connection
  let timeout = config.verified_timeout_seconds * 1000
  const TimeDelay = new Promise((resolve, reject) => {
    setTimeout(resolve, timeout, false)
  })

  var def = deferred()

  var onConnection = async (event) => {
    {
      let payload = event.payload
      if (
        payload.connectionRecord.state === DidExchangeState.Completed
      ) {
        // the connection is now ready for usage in other protocols!
        // console.log(`Connection for out-of-band id ${payload.connectionRecord.outOfBandId} completed`)
        // Custom business logic can be included here
        // In this example we can send a basic message to the connection, but
        // anything is possible

        agent.events.off(
          ConnectionEventTypes.ConnectionStateChanged,
          onConnection
        )

        def.resolve(true)
      }
    }
  }

  agent.events.on(
    ConnectionEventTypes.ConnectionStateChanged,
    onConnection
  )

  const { outOfBandRecord } = await agent.oob.receiveInvitationFromUrl(
    invitationUrl
  )

  // wait for connection
  let value = await Promise.race([TimeDelay, def.promise])

  if (!value) {
    // we no longer need to listen to the event in case of failure
    agent.events.off(
      ConnectionEventTypes.ConnectionStateChanged,
      onConnection
    )
    throw 'Connection timeout!'
  }

  return outOfBandRecord
}

let receiveInvitationConnectionDid = async (agent, invitationUrl) => {
  let timeout = config.verified_timeout_seconds * 1000
  const TimeDelay = new Promise((resolve, reject) => {
    setTimeout(resolve, timeout, false)
  })

  var def = deferred()

  var onConnection = async (event) => {
    {
      let payload = event.payload
      if (
        payload.connectionRecord.state === DidExchangeState.Completed
      ) {
        agent.events.off(
          ConnectionEventTypes.ConnectionStateChanged,
          onConnection
        )

        def.resolve(true)
      }
    }
  }

  agent.events.on(
    ConnectionEventTypes.ConnectionStateChanged,
    onConnection
  )

  let legacyConnectionDid = undefined;
  let connectionId = undefined;
  let oobRecordId = undefined;
  try {
    // LO: need connection record, not OOB record since we need the connection DID
    const { outOfBandRecord, connectionRecord } = await agent.oob.receiveInvitationFromUrl(
      invitationUrl
    )
    const strRes = JSON.stringify(connectionRecord)
    connectionId = connectionRecord.id;
    oobRecordId = outOfBandRecord.id;

    // LO: retrieve the legacy DID. IAS controller needs that to issue against
    // This code adapted from https://github.com/bcgov/bc-wallet-mobile/blob/main/app/src/helpers/BCIDHelper.ts
    const legacyDidKey = '_internal/legacyDid' // TODO:(from BC Wallet code) Waiting for AFJ export of this.
    const didRepository = agent.dependencyManager.resolve(DidRepository)  
    const dids = await didRepository.getAll(agent.context)
    const didRecord = dids.filter((d) => d.did === connectionRecord?.did).pop()
    legacyConnectionDid = didRecord.metadata.get(legacyDidKey)!.unqualifiedDid
  } catch (error) {
    process.stderr.write('******** ERROR'+ '\n' + error + '\n')
  }

  // wait for connection
  let value = await Promise.race([TimeDelay, def.promise])

  if (!value) {
    // we no longer need to listen to the event in case of failure
    agent.events.off(
      ConnectionEventTypes.ConnectionStateChanged,
      onConnection
    )
    throw 'Connection timeout!'
  }

  return { did: legacyConnectionDid, connectionId: connectionId, oobRecordId: oobRecordId}
}

let receiveCredential = async (agent) => {
  // wait for the ping
  let timeout = config.verified_timeout_seconds * 1000

  const TimeDelay = new Promise((resolve, reject) => {
    setTimeout(resolve, timeout, false)
  })

  var def = deferred()

  let onCredential = async (event) => {
    let payload = event.payload

    switch (payload.credentialRecord.state) {
      case CredentialState.OfferReceived:
        //console.log('received a credential')
        // custom logic here
        await agent.credentials.acceptOffer({
          credentialRecordId: payload.credentialRecord.id,
        })
        break
      case CredentialState.CredentialReceived:
        //console.log(`Credential for credential id ${payload.credentialRecord.id} is accepted`)
        // For demo purposes we exit the program here.

        agent.events.off(
          CredentialEventTypes.CredentialStateChanged,
          onCredential
        )

        def.resolve(true)
        break
    }
  }

  agent.events.on(
    CredentialEventTypes.CredentialStateChanged,
    onCredential
  )

  // Nothing for us to do

  // wait for credential
  let value = await Promise.race([TimeDelay, def.promise])

  if (!value) {
    // we no longer need to listen to the event in case of failure
    agent.events.off(
      CredentialEventTypes.CredentialStateChanged,
      onCredential
    )
    throw 'Credential timeout!'
  }
}

let presentationExchange = async (agent) => {
  // wait for the ping
  let timeout = config.verified_timeout_seconds * 1000

  const TimeDelay = new Promise((resolve, reject) => {
    setTimeout(resolve, timeout, false)
  })

  var def = deferred()

  let onRequest = async (event) => {
    let payload = event.payload

    switch (payload.proofRecord.state) {
      case ProofState.RequestReceived:
        const requestedCredentials =
          await agent.proofs.selectCredentialsForRequest({
            proofRecordId: payload.proofRecord.id,
            // config: {
            //   filterByPresentationPreview: true,
            // },
          })
        await agent.proofs.acceptRequest({
          proofRecordId: payload.proofRecord.id,
          proofFormats: requestedCredentials.proofFormats,
        })
        agent.events.off(ProofEventTypes.ProofStateChanged, onRequest)
        def.resolve(true)
        break
    }
  }

  agent.events.on(ProofEventTypes.ProofStateChanged, onRequest)

  // Wait for presentation
  let value = await Promise.race([TimeDelay, def.promise])

  if (!value) {
    // No longer need to listen to the event in case of failure
    agent.events.off(ProofEventTypes.ProofStateChanged, onRequest)
    throw 'Presentation timeout!'
  }
}

let receiveMessage = async (agent) => {
  // wait for the ping
  let timeout = config.verified_timeout_seconds * 1000

  const TimeDelay = new Promise((resolve, reject) => {
    setTimeout(resolve, timeout, false)
  })

  var def = deferred()

  let onMessage = async (event) => {
    let payload = event.payload

    //        console.error(payload)

    agent.events.off(
      BasicMessageEventTypes.BasicMessageStateChanged,
      onMessage
    )

    def.resolve(true)
  }

  agent.events.on(
    BasicMessageEventTypes.BasicMessageStateChanged,
    onMessage
  )

  // Nothing for us to do

  // wait for credential
  let value = await Promise.race([TimeDelay, def.promise])

  if (!value) {
    // we no longer need to listen to the event in case of failure
    agent.events.off(
      BasicMessageEventTypes.BasicMessageStateChanged,
      onMessage
    )
    throw 'Message timeout!'
  }
}

var readline = require('readline')

var rl = readline.createInterface(process.stdin, null)

var agent = null
var agentConfig = null

rl.setPrompt('')
rl.prompt(false)

const handleError = async (e) => {
  throw e;
  process.stdout.write(JSON.stringify({ error: 1, result: e }) + '\n')
}

rl.on('line', async (line) => {
  try {
    var command = JSON.parse(line)

    if (command['cmd'] == 'start') {
      [agent, agentConfig] = await initializeAgent(
        command['withMediation'],
        command['port'],
        command['agentConfig']
      )
      // if (command["agentConfig"] === null || !command["agentConfig"]) {
      //   [agent, agentConfig] = await initializeAgent(
      //     command["withMediation"],
      //     command["port"]
      //   );
      // } else {
      //   [agent, agentConfig] = await initializeAgent();
      // }
      // process.stdout.write(
      //   JSON.stringify({ error: 0, result: "Initialized agent..." }) + "\n"
      // );
      process.stdout.write(
        JSON.stringify({ error: 0, result: agentConfig }) + '\n'
      )
    } else if (command['cmd'] == 'ping_mediator') {
      await pingMediator(agent)
      process.stdout.write(
        JSON.stringify({ error: 0, result: 'Ping Mediator' }) + '\n'
      )
    } else if (command['cmd'] == 'deleteOobRecordById') {
      await deleteOobRecordById(agent, command['id'])

      process.stdout.write(
        JSON.stringify({ error: 0, result: 'Delete OOB Record' }) + '\n'
      )
    } else if (command['cmd'] == 'receiveInvitation') {
      let connection = await receiveInvitation(agent, command['invitationUrl'])

      process.stdout.write(
        JSON.stringify({
          error: 0,
          result: 'Receive Connection',
          connection: connection,
        }) + '\n'
      )
    } else if (command['cmd'] == 'receiveInvitationConnectionDid') {
      let connection = await receiveInvitationConnectionDid(agent, command['invitationUrl'])

      process.stdout.write(
        JSON.stringify({
          error: 0,
          result: 'Receive Invitation Connection',
          connection: connection,
        }) + '\n'
      )
    } else if (command['cmd'] == 'receiveCredential') {
      await receiveCredential(agent)

      process.stdout.write(
        JSON.stringify({ error: 0, result: 'Receive Credential' }) + '\n'
      )
    } else if (command['cmd'] == 'presentationExchange') {
      await presentationExchange(agent)

      process.stdout.write(
        JSON.stringify({ error: 0, result: 'Presentation Exchange' }) + '\n'
      )
    } else if (command['cmd'] == 'receiveMessage') {
      await receiveMessage(agent)

      process.stdout.write(
        JSON.stringify({ error: 0, result: 'Receive Message' }) + '\n'
      )
    } else if (command['cmd'] == 'shutdown') {
      process.stdout.write(
        JSON.stringify({ error: 0, result: 'Shutting down agent' }) + '\n'
      )
      rl.close()
      await agent.shutdown()
      process.exit(1)
    } else {
      handleError('Invalid command')
    }
  } catch (e) {
    if (e.name === 'JSONDecodeError') {
      process.stdout.write(
        JSON.stringify({ error: 0, result: 'JSONDecodeError received' }) + '\n'
      )
    }
    handleError(e)
  }
})

process.once('SIGTERM', function (code) {
  process.stderr.write('SIGTERM received...' + '\n')
  process.exit(1)
})
