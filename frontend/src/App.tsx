
import { useRef, useState, type FormEvent } from 'react'
import './App.css'

type NegotiationMode = 'MANUAL' | 'AUTONOMOUS'

type NegotiationStatus =
  | 'CREATED'
  | 'PENDING_APPROVAL'
  | 'PENDING_FINAL_APPROVAL'
  | 'ACTIVE'
  | 'COMPLETED'
  | 'CANCELLED'

type ApprovalAction = 'APPROVE' | 'REJECT' | 'MODIFY'
type FinalApprovalAction = 'CONFIRM' | 'REJECT'

type Offer = {
  amount: number
  message: string
}

type HistoryMessage = {
  role: string
  content: string
}

type NegotiationConfig = {
  item: string
  target_price: number
  max_budget: number
  opening_offer: number
  mode: NegotiationMode
  max_rounds: number
}

type NegotiationSession = {
  session_id: string
  status: NegotiationStatus
  config: NegotiationConfig
  pending_offer: Offer | null
  last_approved_amount: number | null
  round_number: number
  messages: HistoryMessage[]
}

type CreateResponse = {
  session_id: string
  status: NegotiationStatus
  config: NegotiationConfig
}

type OpeningOfferResponse = {
  session_id: string
  status: NegotiationStatus
  proposed_amount: number
  message: string
}

type SellerResponseResult = {
  session_id: string
  status: NegotiationStatus
  outcome:
    | 'ACCEPTED'
    | 'REJECTED'
    | 'CONTINUE'
    | 'NEEDS_CONFIRMATION'
    | 'MAX_ROUNDS_REACHED'
  reason?: string
  message?: string
  proposed_amount?: number
  agreed_amount?: number
}

function App() {
  const [item, setItem] = useState('')
  const [targetPrice, setTargetPrice] = useState('')
  const [maxBudget, setMaxBudget] = useState('')
  const [openingOffer, setOpeningOffer] = useState('')

  const [mode, setMode] = useState<NegotiationMode>('MANUAL')
  const [maxRounds, setMaxRounds] = useState('5')

  const [sessionId, setSessionId] = useState('')
  const [status, setStatus] = useState<NegotiationStatus | ''>('')

  const [sessionConfig, setSessionConfig] =
    useState<NegotiationConfig | null>(null)

  const [roundNumber, setRoundNumber] = useState(0)

  const [pendingOffer, setPendingOffer] =
    useState<Offer | null>(null)

  const [lastApprovedAmount, setLastApprovedAmount] =
    useState<number | null>(null)

  const [modifiedAmount, setModifiedAmount] = useState('')
  const [showModify, setShowModify] = useState(false)

  const [sellerMessage, setSellerMessage] = useState('')

  const [sellerOutcome, setSellerOutcome] =
    useState<SellerResponseResult | null>(null)

  const [history, setHistory] = useState<HistoryMessage[]>([])

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [loading, setLoading] = useState(false)
  const [offerLoading, setOfferLoading] = useState(false)
  const [approvalLoading, setApprovalLoading] = useState(false)
  const [sellerLoading, setSellerLoading] = useState(false)
  const [finalApprovalLoading, setFinalApprovalLoading] =
    useState(false)

  const createLock = useRef(false)
  const offerLock = useRef(false)
  const approvalLock = useRef(false)
  const sellerLock = useRef(false)
  const finalApprovalLock = useRef(false)

  const activeMode = sessionConfig?.mode ?? 'MANUAL'

  function formatPrice(amount: number): string {
    return amount.toLocaleString('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })
  }

  async function readError(response: Response): Promise<string> {
    let detail = response.statusText

    try {
      const data: unknown = await response.json()

      if (
        typeof data === 'object' &&
        data !== null &&
        'detail' in data
      ) {
        const value = (data as { detail: unknown }).detail

        detail =
          typeof value === 'string'
            ? value
            : JSON.stringify(value)
      }
    } catch {
      // Response may not contain JSON.
    }

    return `Backend error ${response.status}: ${detail}`
  }

  async function refreshSession(id: string) {
    const response = await fetch(
      `/api/v1/negotiations/${id}`
    )

    if (!response.ok) {
      throw new Error(await readError(response))
    }

    const data: NegotiationSession = await response.json()

    setStatus(data.status)
    setSessionConfig(data.config)
    setPendingOffer(data.pending_offer ?? null)
    setLastApprovedAmount(data.last_approved_amount ?? null)
    setRoundNumber(data.round_number)
    setHistory(data.messages ?? [])

    if (data.pending_offer) {
      setModifiedAmount(String(data.pending_offer.amount))
    }

    return data
  }

  async function startNegotiation(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault()

    if (createLock.current) return

    setError('')
    setSuccess('')

    const target = Number(targetPrice)
    const budget = Number(maxBudget)
    const opening = Number(openingOffer)
    const rounds = Number(maxRounds)

    if (!item.trim()) {
      setError('Please enter an item.')
      return
    }

    if (
      !targetPrice.trim() ||
      !maxBudget.trim() ||
      !openingOffer.trim() ||
      !Number.isFinite(target) ||
      !Number.isFinite(budget) ||
      !Number.isFinite(opening) ||
      target <= 0 ||
      budget <= 0 ||
      opening <= 0
    ) {
      setError('All prices must be valid positive numbers.')
      return
    }

    if (opening > target || target > budget) {
      setError(
        'Opening offer must be <= target price <= maximum budget.'
      )
      return
    }

    if (
      !maxRounds.trim() ||
      !Number.isInteger(rounds) ||
      rounds < 1 ||
      rounds > 20
    ) {
      setError(
        'Maximum rounds must be a whole number between 1 and 20.'
      )
      return
    }

    const config: NegotiationConfig = {
      item: item.trim(),
      target_price: target,
      max_budget: budget,
      opening_offer: opening,
      mode,
      max_rounds: rounds,
    }

    createLock.current = true
    setLoading(true)

    try {
      const response = await fetch(
        '/api/v1/negotiations',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(config),
        }
      )

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const data: CreateResponse = await response.json()

      setSessionId(data.session_id)
      setStatus(data.status)
      setSessionConfig(data.config ?? config)
      setRoundNumber(0)
      setPendingOffer(null)
      setLastApprovedAmount(null)
      setModifiedAmount('')
      setShowModify(false)
      setSellerMessage('')
      setSellerOutcome(null)
      setHistory([])

      setSuccess(
        `${mode === 'AUTONOMOUS' ? 'Autonomous' : 'Manual'} negotiation created successfully.`
      )
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not create negotiation.'
      )
    } finally {
      createLock.current = false
      setLoading(false)
    }
  }

  async function generateOpeningOffer() {
    if (
      !sessionId ||
      status !== 'CREATED' ||
      pendingOffer ||
      offerLock.current
    ) {
      return
    }

    offerLock.current = true
    setOfferLoading(true)
    setError('')
    setSuccess('')

    try {
      const response = await fetch(
        `/api/v1/negotiations/${sessionId}/opening-offer`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const data: OpeningOfferResponse =
        await response.json()

      if (
        !Number.isFinite(data.proposed_amount) ||
        typeof data.message !== 'string'
      ) {
        throw new Error(
          'Invalid opening offer response.'
        )
      }

      await refreshSession(sessionId)

      setShowModify(false)

      if (data.status === 'ACTIVE') {
        setSuccess(
          'Opening offer automatically approved within your limits.'
        )
      } else {
        setSuccess(
          'Opening offer generated. Your approval is required.'
        )
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not generate opening offer.'
      )

      try {
        await refreshSession(sessionId)
      } catch {
        // Preserve original error.
      }
    } finally {
      offerLock.current = false
      setOfferLoading(false)
    }
  }

  async function submitApproval(action: ApprovalAction) {
    if (
      !sessionId ||
      !pendingOffer ||
      status !== 'PENDING_APPROVAL' ||
      approvalLock.current
    ) {
      return
    }

    let amount: number | undefined

    if (action === 'MODIFY') {
      if (!modifiedAmount.trim()) {
        setError('Enter a modified offer amount.')
        return
      }

      amount = Number(modifiedAmount)

      if (
        !Number.isFinite(amount) ||
        amount <= 0
      ) {
        setError(
          'Modified amount must be greater than zero.'
        )
        return
      }

      const budget =
        sessionConfig?.max_budget ?? Number(maxBudget)

      if (amount > budget) {
        setError(
          `Offer cannot exceed your maximum budget of ${formatPrice(budget)}.`
        )
        return
      }
    }

    approvalLock.current = true
    setApprovalLoading(true)
    setError('')
    setSuccess('')

    try {
      const payload: {
        action: ApprovalAction
        modified_amount?: number
      } = { action }

      if (
        action === 'MODIFY' &&
        amount !== undefined
      ) {
        payload.modified_amount = amount
      }

      const response = await fetch(
        `/api/v1/negotiations/${sessionId}/approval`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }
      )

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      await refreshSession(sessionId)

      setShowModify(false)

      if (action === 'REJECT') {
        setSuccess(
          'Offer rejected. Nothing was sent to the seller.'
        )
      } else if (action === 'MODIFY') {
        setSuccess(
          'Modified offer approved and recorded locally.'
        )
      } else {
        setSuccess(
          'Offer approved and recorded locally.'
        )
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Approval failed.'
      )

      try {
        await refreshSession(sessionId)
      } catch {
        // Preserve original error.
      }
    } finally {
      approvalLock.current = false
      setApprovalLoading(false)
    }
  }

  async function submitSellerResponse() {
    if (
      !sessionId ||
      status !== 'ACTIVE' ||
      sellerLock.current
    ) {
      return
    }

    if (!sellerMessage.trim()) {
      setError(
        'Please enter the seller response.'
      )
      return
    }

    sellerLock.current = true
    setSellerLoading(true)
    setError('')
    setSuccess('')
    setSellerOutcome(null)

    try {
      const response = await fetch(
        `/api/v1/negotiations/${sessionId}/seller-response`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: sellerMessage.trim(),
          }),
        }
      )

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const result: SellerResponseResult =
        await response.json()

      setSellerOutcome(result)

      await refreshSession(sessionId)

      if (result.outcome === 'CONTINUE') {
        if (result.status === 'ACTIVE') {
          setSuccess(
            'AI generated and automatically approved a counteroffer within your limits.'
          )
        } else {
          setSuccess(
            'AI counteroffer generated. Please review and approve it.'
          )
        }
      } else if (result.outcome === 'ACCEPTED') {
        setSuccess(
          'Seller acceptance detected. Your final confirmation is required.'
        )
      } else if (result.outcome === 'REJECTED') {
        setSuccess(
          'Seller rejection detected. Negotiation cancelled.'
        )
      } else if (
        result.outcome === 'NEEDS_CONFIRMATION'
      ) {
        setSuccess(
          'Seller response needs clarification. No agreement was recorded.'
        )
      } else if (
        result.outcome === 'MAX_ROUNDS_REACHED'
      ) {
        setSuccess(
          'Maximum negotiation rounds reached. Negotiation ended.'
        )
      }

      setSellerMessage('')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not process seller response.'
      )

      try {
        await refreshSession(sessionId)
      } catch {
        // Preserve original error.
      }
    } finally {
      sellerLock.current = false
      setSellerLoading(false)
    }
  }

  async function submitFinalApproval(
    action: FinalApprovalAction
  ) {
    if (
      !sessionId ||
      status !== 'PENDING_FINAL_APPROVAL' ||
      finalApprovalLock.current
    ) {
      return
    }

    finalApprovalLock.current = true
    setFinalApprovalLoading(true)
    setError('')
    setSuccess('')

    try {
      const response = await fetch(
        `/api/v1/negotiations/${sessionId}/final-approval`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ action }),
        }
      )

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      await refreshSession(sessionId)

      if (action === 'CONFIRM') {
        setSuccess(
          'Agreement confirmed locally. No payment or transaction was executed.'
        )
      } else {
        setSuccess(
          'Agreement rejected by buyer. Negotiation cancelled.'
        )
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Final approval failed.'
      )

      try {
        await refreshSession(sessionId)
      } catch {
        // Preserve original error.
      }
    } finally {
      finalApprovalLock.current = false
      setFinalApprovalLoading(false)
    }
  }

  const latestBuyerMessage = [...history]
    .reverse()
    .find((message) => message.role === 'buyer')

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <div className="brand">
          <div className="brand-icon">N</div>

          <div>
            <h1>NegotiateAI</h1>
            <p>Your AI-powered negotiation workspace</p>
          </div>
        </div>

        <span className="header-tag">
          AI Negotiation Assistant
        </span>
      </header>

      <div className="dashboard-grid">
        <section className="dashboard-card setup-card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">GET STARTED</span>
              <h2>Negotiation Setup</h2>
            </div>
          </div>

          <p className="card-description">
            Define your goals and let AI help you negotiate
            within your limits.
          </p>

          <form
            className="setup-form"
            onSubmit={startNegotiation}
          >
            <div className="field">
              <label htmlFor="item">
                What are you negotiating?
              </label>

              <input
                id="item"
                value={item}
                onChange={(event) =>
                  setItem(event.target.value)
                }
                placeholder="e.g. Used MacBook Pro"
                required
              />
            </div>

            <div className="field-grid">
              <div className="field">
                <label htmlFor="targetPrice">
                  Target Price ($)
                </label>

                <input
                  id="targetPrice"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={targetPrice}
                  onChange={(event) =>
                    setTargetPrice(event.target.value)
                  }
                  placeholder="400"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="maxBudget">
                  Maximum Budget ($)
                </label>

                <input
                  id="maxBudget"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={maxBudget}
                  onChange={(event) =>
                    setMaxBudget(event.target.value)
                  }
                  placeholder="500"
                  required
                />
              </div>
            </div>

            <div className="field-grid">
              <div className="field">
                <label htmlFor="openingOffer">
                  Opening Offer ($)
                </label>

                <input
                  id="openingOffer"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={openingOffer}
                  onChange={(event) =>
                    setOpeningOffer(event.target.value)
                  }
                  placeholder="300"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="maxRounds">
                  Maximum Rounds
                </label>

                <input
                  id="maxRounds"
                  type="number"
                  min="1"
                  max="20"
                  step="1"
                  value={maxRounds}
                  onChange={(event) =>
                    setMaxRounds(event.target.value)
                  }
                  required
                />
              </div>
            </div>

            <div className="field">
              <label htmlFor="mode">
                Negotiation Mode
              </label>

              <select
                id="mode"
                value={mode}
                onChange={(event) =>
                  setMode(
                    event.target.value as NegotiationMode
                  )
                }
              >
                <option value="MANUAL">
                  Manual - approve every offer
                </option>

                <option value="AUTONOMOUS">
                  Autonomous - AI approves within limits
                </option>
              </select>
            </div>

            <div className="info-note">
              AI offers stay within your budget and round limits.
              Offers are not sent to sellers automatically.
              Final buyer approval is always required.
            </div>

            <button
              className="primary-button full-width"
              type="submit"
              disabled={loading}
            >
              {loading
                ? 'Creating Negotiation...'
                : 'Start Negotiation'}
            </button>
          </form>
        </section>

        <section className="dashboard-card workspace-card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">
                AI WORKSPACE
              </span>

              <h2>Negotiation Workspace</h2>
            </div>

            <span
              className={`status-badge ${
                status ? status.toLowerCase() : 'idle'
              }`}
            >
              {status
                ? status.replaceAll('_', ' ')
                : 'READY'}
            </span>
          </div>

          {!sessionId ? (
            <div className="empty-workspace">
              <div className="empty-icon">✦</div>

              <h3>Ready to negotiate?</h3>

              <p>
                Configure your negotiation on the left
                and start a session to see AI-powered
                offers here.
              </p>

              <div className="empty-steps">
                <span>1. Set your limits</span>
                <span>2. Generate an offer</span>
                <span>3. Negotiate with AI</span>
              </div>
            </div>
          ) : (
            <div className="session-content">
              <div className="session-summary">
                <div className="summary-item">
                  <span>Negotiation Mode</span>
                  <strong>{activeMode}</strong>
                </div>

                <div className="summary-item">
                  <span>Buyer Offers</span>
                  <strong>
                    {roundNumber} /{' '}
                    {sessionConfig?.max_rounds ?? 0}
                  </strong>
                </div>

                <div className="summary-item">
                  <span>Maximum Budget</span>

                  <strong>
                    {sessionConfig
                      ? formatPrice(
                          sessionConfig.max_budget
                        )
                      : '-'}
                  </strong>
                </div>
              </div>

              <p className="session-id">
                Session: {sessionId}
              </p>

              {status === 'CREATED' &&
                !pendingOffer && (
                  <div className="action-panel">
                    <h3>Your negotiation is ready</h3>

                    <p>
                      Generate your opening offer to begin.
                    </p>

                    <button
                      type="button"
                      onClick={generateOpeningOffer}
                      disabled={offerLoading}
                    >
                      {offerLoading
                        ? 'Generating...'
                        : 'Generate Opening Offer'}
                    </button>
                  </div>
                )}

              {status === 'PENDING_APPROVAL' &&
                pendingOffer && (
                  <div className="action-panel">
                    <span className="eyebrow">
                      YOUR APPROVAL REQUIRED
                    </span>

                    <h3>Review AI Offer</h3>

                    <div className="offer-amount">
                      {formatPrice(
                        pendingOffer.amount
                      )}
                    </div>

                    <div className="message-box">
                      {pendingOffer.message}
                    </div>

                    <div className="button-row">
                      <button
                        type="button"
                        onClick={() =>
                          submitApproval('APPROVE')
                        }
                        disabled={approvalLoading}
                      >
                        Approve
                      </button>

                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => {
                          setShowModify(!showModify)
                          setModifiedAmount(
                            String(pendingOffer.amount)
                          )
                          setError('')
                        }}
                        disabled={approvalLoading}
                      >
                        Modify
                      </button>

                      <button
                        type="button"
                        className="danger-button"
                        onClick={() =>
                          submitApproval('REJECT')
                        }
                        disabled={approvalLoading}
                      >
                        Reject
                      </button>
                    </div>

                    {showModify && (
                      <div className="modify-panel">
                        <label htmlFor="modifiedAmount">
                          New Offer Amount ($)
                        </label>

                        <input
                          id="modifiedAmount"
                          type="number"
                          min="0.01"
                          step="0.01"
                          max={
                            sessionConfig?.max_budget ??
                            maxBudget
                          }
                          value={modifiedAmount}
                          onChange={(event) =>
                            setModifiedAmount(
                              event.target.value
                            )
                          }
                        />

                        <button
                          type="button"
                          onClick={() =>
                            submitApproval('MODIFY')
                          }
                          disabled={approvalLoading}
                        >
                          {approvalLoading
                            ? 'Processing...'
                            : 'Confirm Modified Offer'}
                        </button>
                      </div>
                    )}
                  </div>
                )}

              {status === 'ACTIVE' && (
                <div className="action-panel">
                  <span className="eyebrow">
                    NEGOTIATION IN PROGRESS
                  </span>

                  <h3>Active Negotiation</h3>

                  {activeMode === 'AUTONOMOUS' && (
                    <div className="info-note">
                      Autonomous mode is active.
                      AI offers are approved automatically
                      within your limits. You still
                      communicate with the seller manually.
                    </div>
                  )}

                  {lastApprovedAmount !== null && (
                    <div className="approved-offer">
                      <span>
                        Last Approved Offer
                      </span>

                      <strong>
                        {formatPrice(
                          lastApprovedAmount
                        )}
                      </strong>
                    </div>
                  )}

                  {latestBuyerMessage && (
                    <div className="message-box">
                      <h4>
                        Approved Buyer Message
                      </h4>

                      <p>
                        {latestBuyerMessage.content}
                      </p>
                    </div>
                  )}

                  <p className="helper-text">
                    Share the approved message with
                    the seller, then paste their
                    response below.
                  </p>

                  <div className="field">
                    <label htmlFor="sellerMessage">
                      Seller's Response
                    </label>

                    <textarea
                      id="sellerMessage"
                      rows={4}
                      value={sellerMessage}
                      onChange={(event) =>
                        setSellerMessage(
                          event.target.value
                        )
                      }
                      placeholder="Enter the seller's message..."
                    />
                  </div>

                  <button
                    type="button"
                    onClick={submitSellerResponse}
                    disabled={
                      sellerLoading ||
                      !sellerMessage.trim()
                    }
                  >
                    {sellerLoading
                      ? 'Processing Seller Response...'
                      : 'Process Seller Response'}
                  </button>

                  {sellerOutcome?.outcome ===
                    'NEEDS_CONFIRMATION' && (
                    <div className="info-note">
                      <strong>
                        Clarification Required
                      </strong>

                      <p>
                        {sellerOutcome.message ||
                          'Ask the seller to confirm the exact price.'}
                      </p>

                      {sellerOutcome.reason && (
                        <p>
                          {sellerOutcome.reason}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {status ===
                'PENDING_FINAL_APPROVAL' && (
                <div className="action-panel">
                  <span className="eyebrow">
                    FINAL DECISION
                  </span>

                  <h3>Final Buyer Approval</h3>

                  <p>
                    The seller accepted your offer.
                    Review the agreed amount before
                    confirming.
                  </p>

                  {lastApprovedAmount !== null && (
                    <div className="offer-amount">
                      {formatPrice(
                        lastApprovedAmount
                      )}
                    </div>
                  )}

                  <div className="info-note">
                    Confirming records the agreement
                    locally. No payment, purchase,
                    or external transaction will
                    be executed.
                  </div>

                  <div className="button-row">
                    <button
                      type="button"
                      onClick={() =>
                        submitFinalApproval('CONFIRM')
                      }
                      disabled={finalApprovalLoading}
                    >
                      {finalApprovalLoading
                        ? 'Processing...'
                        : 'Confirm Agreement'}
                    </button>

                    <button
                      type="button"
                      className="danger-button"
                      onClick={() =>
                        submitFinalApproval('REJECT')
                      }
                      disabled={finalApprovalLoading}
                    >
                      Reject Agreement
                    </button>
                  </div>
                </div>
              )}

              {status === 'COMPLETED' && (
                <div className="result-panel">
                  <h3>
                    ✓ Negotiation Completed
                  </h3>

                  <p>
                    The buyer confirmed the agreement.
                  </p>

                  {lastApprovedAmount !== null && (
                    <div className="offer-amount">
                      {formatPrice(
                        lastApprovedAmount
                      )}
                    </div>
                  )}

                  <p>
                    Recorded locally. No payment
                    or external transaction
                    was executed.
                  </p>
                </div>
              )}

              {status === 'CANCELLED' && (
                <div className="action-panel">
                  <h3>
                    Negotiation Cancelled
                  </h3>

                  <p>
                    The negotiation has ended.
                  </p>
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {error && (
        <div
          className="feedback-error"
          role="alert"
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {success && (
        <div
          className="feedback-success"
          role="status"
        >
          {success}
        </div>
      )}

      <section className="dashboard-card history-card">
        <div className="card-heading">
          <div>
            <span className="eyebrow">
              ACTIVITY LOG
            </span>

            <h2>Negotiation History</h2>
          </div>

          <span className="history-count">
            {history.length} messages
          </span>
        </div>

        {history.length === 0 ? (
          <p className="history-empty">
            Your negotiation history will
            appear here once the conversation begins.
          </p>
        ) : (
          <div className="history-list">
            {history.map((message, index) => (
              <div
                className={`history-message ${message.role}`}
                key={index}
              >
                <div className="history-avatar">
                  {message.role === 'buyer'
                    ? 'B'
                    : message.role === 'seller'
                      ? 'S'
                      : 'AI'}
                </div>

                <div>
                  <strong>
                    {message.role === 'buyer'
                      ? 'Buyer'
                      : message.role === 'seller'
                        ? 'Seller'
                        : message.role}
                  </strong>

                  <p>{message.content}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <footer className="dashboard-footer">
        NegotiateAI · AI-assisted negotiations ·
        Offers are recorded locally,
        not sent automatically
      </footer>
    </main>
  )
}

export default App
