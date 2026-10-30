import { useRef, useState, type FormEvent } from 'react'
import './App.css'

type Offer = {
  amount: number
  message: string
}

type ApprovalAction = 'APPROVE' | 'REJECT' | 'MODIFY'

type NegotiationStatus =
  | 'CREATED'
  | 'PENDING_APPROVAL'
  | 'ACTIVE'
  | 'COMPLETED'
  | 'CANCELLED'

type NegotiationSession = {
  session_id: string
  status: NegotiationStatus
  pending_offer: Offer | null
  last_approved_amount: number | null
  round_number: number
  messages: Array<{
    role: string
    content: string
  }>
}

type CreateResponse = {
  session_id: string
  status: NegotiationStatus
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
  outcome: 'ACCEPTED' | 'REJECTED' | 'CONTINUE' | 'NEEDS_CONFIRMATION'
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

  const [sessionId, setSessionId] = useState('')
  const [status, setStatus] = useState<NegotiationStatus | ''>('')

  const [pendingOffer, setPendingOffer] = useState<Offer | null>(null)
  const [lastApprovedAmount, setLastApprovedAmount] =
    useState<number | null>(null)

  const [modifiedAmount, setModifiedAmount] = useState('')
  const [showModify, setShowModify] = useState(false)

  const [sellerMessage, setSellerMessage] = useState('')
  const [sellerOutcome, setSellerOutcome] =
    useState<SellerResponseResult | null>(null)

  const [history, setHistory] = useState<
    Array<{ role: string; content: string }>
  >([])

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [loading, setLoading] = useState(false)
  const [offerLoading, setOfferLoading] = useState(false)
  const [approvalLoading, setApprovalLoading] = useState(false)
  const [sellerLoading, setSellerLoading] = useState(false)

  const createLock = useRef(false)
  const offerLock = useRef(false)
  const approvalLock = useRef(false)
  const sellerLock = useRef(false)

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
      // The response may not contain JSON.
    }

    return `Backend error ${response.status}: ${detail}`
  }

  async function refreshSession(id: string) {
    const response = await fetch(`/api/v1/negotiations/${id}`)

    if (!response.ok) {
      throw new Error(await readError(response))
    }

    const data: NegotiationSession = await response.json()

    setStatus(data.status)
    setPendingOffer(data.pending_offer ?? null)
    setLastApprovedAmount(data.last_approved_amount ?? null)
    setHistory(data.messages ?? [])

    if (data.pending_offer) {
      setModifiedAmount(String(data.pending_offer.amount))
    }

    return data
  }

  async function startNegotiation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (createLock.current) return

    setError('')
    setSuccess('')

    const target = Number(targetPrice)
    const budget = Number(maxBudget)
    const opening = Number(openingOffer)

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
        'Opening offer must be ≤ target price ≤ maximum budget.'
      )
      return
    }

    createLock.current = true
    setLoading(true)

    try {
      const response = await fetch('/api/v1/negotiations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          item: item.trim(),
          target_price: target,
          max_budget: budget,
          opening_offer: opening,
        }),
      })

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const data: CreateResponse = await response.json()

      setSessionId(data.session_id)
      setStatus(data.status)
      setPendingOffer(null)
      setLastApprovedAmount(null)
      setModifiedAmount('')
      setShowModify(false)
      setSellerMessage('')
      setSellerOutcome(null)
      setHistory([])

      setSuccess('Negotiation session created successfully.')
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
        { method: 'POST' }
      )

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      const data: OpeningOfferResponse = await response.json()

      if (
        !Number.isFinite(data.proposed_amount) ||
        typeof data.message !== 'string'
      ) {
        throw new Error('Invalid opening offer response.')
      }

      setPendingOffer({
        amount: data.proposed_amount,
        message: data.message,
      })

      setModifiedAmount(String(data.proposed_amount))
      setStatus(data.status)
      setShowModify(false)

      setSuccess('Opening offer generated. Approval required.')
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

      if (!Number.isFinite(amount) || amount <= 0) {
        setError('Modified amount must be greater than zero.')
        return
      }

      if (amount > Number(maxBudget)) {
        setError(
          `Offer cannot exceed your maximum budget of $${maxBudget}.`
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

      if (action === 'MODIFY' && amount !== undefined) {
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
        setSuccess('Offer rejected. Nothing was sent to the seller.')
      } else if (action === 'MODIFY') {
        setSuccess(
          'Modified offer approved and recorded locally.'
        )
      } else {
        setSuccess('Offer approved and recorded locally.')
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
      setError('Please enter the seller response.')
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

      const result: SellerResponseResult = await response.json()

      setSellerOutcome(result)

      await refreshSession(sessionId)

      if (result.outcome === 'CONTINUE') {
        setSuccess(
          'AI counteroffer generated. Please review and approve it.'
        )
      } else if (result.outcome === 'ACCEPTED') {
        setSuccess(
          'Seller acceptance detected. Negotiation marked as completed locally.'
        )
      } else if (result.outcome === 'REJECTED') {
        setSuccess(
          'Seller rejection detected. Negotiation marked as cancelled.'
        )
      } else if (result.outcome === 'NEEDS_CONFIRMATION') {
        setSuccess(
          'Seller response needs clarification. No agreement was recorded.'
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

  const latestBuyerMessage = [...history]
    .reverse()
    .find((message) => message.role === 'buyer')

  return (
    <main>
      <h1>NegotiateAI</h1>

      <p>Your AI-powered negotiation assistant</p>

      <h2>Start a Negotiation</h2>

      <form onSubmit={startNegotiation}>
        <label htmlFor="item">
          What are you negotiating?
        </label>

        <input
          id="item"
          value={item}
          onChange={(event) => setItem(event.target.value)}
          placeholder="e.g. Used MacBook Pro"
          required
        />

        <label htmlFor="targetPrice">
          Target price ($)
        </label>

        <input
          id="targetPrice"
          type="number"
          min="0.01"
          step="0.01"
          value={targetPrice}
          onChange={(event) => setTargetPrice(event.target.value)}
          required
        />

        <label htmlFor="maxBudget">
          Maximum budget ($)
        </label>

        <input
          id="maxBudget"
          type="number"
          min="0.01"
          step="0.01"
          value={maxBudget}
          onChange={(event) => setMaxBudget(event.target.value)}
          required
        />

        <label htmlFor="openingOffer">
          Opening offer ($)
        </label>

        <input
          id="openingOffer"
          type="number"
          min="0.01"
          step="0.01"
          value={openingOffer}
          onChange={(event) => setOpeningOffer(event.target.value)}
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Creating...' : 'Start Negotiation'}
        </button>
      </form>

      {error && (
        <div
          role="alert"
          style={{
            color: '#991b1b',
            background: '#fee2e2',
            padding: '12px',
            marginTop: '16px',
            borderRadius: '8px',
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {success && (
        <div
          role="status"
          style={{
            color: '#166534',
            background: '#dcfce7',
            padding: '12px',
            marginTop: '16px',
            borderRadius: '8px',
          }}
        >
          {success}
        </div>
      )}

      {sessionId && (
        <section>
          <h2>Negotiation Session</h2>

          <p>
            <strong>Session ID:</strong> {sessionId}
          </p>

          <p>
            <strong>Status:</strong> {status}
          </p>

          {status === 'CREATED' && !pendingOffer && (
            <button
              type="button"
              onClick={generateOpeningOffer}
              disabled={offerLoading}
            >
              {offerLoading
                ? 'Generating...'
                : 'Generate Opening Offer'}
            </button>
          )}

          {status === 'PENDING_APPROVAL' && pendingOffer && (
            <div>
              <h3>Offer Awaiting Your Approval</h3>

              <p>
                <strong>Amount:</strong> ${pendingOffer.amount}
              </p>

              <p>
                <strong>Message:</strong> {pendingOffer.message}
              </p>

              <p>
                <strong>Status:</strong> PENDING_APPROVAL
              </p>

              <div
                style={{
                  display: 'flex',
                  gap: '10px',
                  flexWrap: 'wrap',
                  marginTop: '16px',
                }}
              >
                <button
                  type="button"
                  onClick={() => submitApproval('APPROVE')}
                  disabled={approvalLoading}
                >
                  Approve
                </button>

                <button
                  type="button"
                  onClick={() => submitApproval('REJECT')}
                  disabled={approvalLoading}
                >
                  Reject
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setShowModify(!showModify)
                    setModifiedAmount(String(pendingOffer.amount))
                    setError('')
                  }}
                  disabled={approvalLoading}
                >
                  Modify
                </button>
              </div>

              {showModify && (
                <div style={{ marginTop: '20px' }}>
                  <h4>Modify Offer</h4>

                  <label htmlFor="modifiedAmount">
                    New offer amount ($)
                  </label>

                  <input
                    id="modifiedAmount"
                    type="number"
                    min="0.01"
                    step="0.01"
                    max={maxBudget}
                    value={modifiedAmount}
                    onChange={(event) =>
                      setModifiedAmount(event.target.value)
                    }
                  />

                  <button
                    type="button"
                    onClick={() => submitApproval('MODIFY')}
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
            <div>
              <h3>Active Negotiation</h3>

              {lastApprovedAmount !== null && (
                <p>
                  <strong>Last approved offer:</strong> $
                  {lastApprovedAmount}
                </p>
              )}

              {latestBuyerMessage && (
                <div>
                  <h4>Last Approved Buyer Message</h4>
                  <p>{latestBuyerMessage.content}</p>
                </div>
              )}

              <p>
                Share your approved offer with the seller manually.
                Then enter the seller's response below.
              </p>

              <h3>Seller's Response</h3>

              <label htmlFor="sellerMessage">
                Enter the seller's message
              </label>

              <textarea
                id="sellerMessage"
                rows={5}
                value={sellerMessage}
                onChange={(event) =>
                  setSellerMessage(event.target.value)
                }
                placeholder="e.g. I can't accept $360, but I could sell it for $450."
                style={{
                  display: 'block',
                  width: '100%',
                  maxWidth: '600px',
                  boxSizing: 'border-box',
                  padding: '12px',
                  marginTop: '10px',
                  marginBottom: '16px',
                }}
              />

              <button
                type="button"
                onClick={submitSellerResponse}
                disabled={sellerLoading || !sellerMessage.trim()}
              >
                {sellerLoading
                  ? 'Processing Seller Response...'
                  : 'Process Seller Response'}
              </button>

              {sellerOutcome?.outcome === 'NEEDS_CONFIRMATION' && (
                <div>
                  <h4>Clarification Required</h4>
                  <p>
                    {sellerOutcome.message ||
                      'Ask the seller to confirm the exact price.'}
                  </p>
                  {sellerOutcome.reason && (
                    <p>{sellerOutcome.reason}</p>
                  )}
                </div>
              )}
            </div>
          )}

          {status === 'COMPLETED' && (
            <div>
              <h3>Negotiation Completed</h3>

              <p>Seller acceptance was detected.</p>

              {sellerOutcome?.agreed_amount !== undefined && (
                <p>
                  <strong>Agreed amount:</strong> $
                  {sellerOutcome.agreed_amount}
                </p>
              )}

              <p>
                This outcome was recorded locally.
                No payment or external transaction was executed.
              </p>
            </div>
          )}

          {status === 'CANCELLED' && (
            <div>
              <h3>Negotiation Cancelled</h3>
              <p>The negotiation has ended.</p>
            </div>
          )}

          {history.length > 0 && (
            <div>
              <h3>Negotiation History</h3>

              {history.map((message, index) => (
                <div
                  key={index}
                  style={{
                    border: '1px solid #ddd',
                    borderRadius: '8px',
                    padding: '12px',
                    marginBottom: '10px',
                  }}
                >
                  <strong>
                    {message.role === 'buyer'
                      ? 'Buyer'
                      : message.role === 'seller'
                        ? 'Seller'
                        : message.role}
                  </strong>

                  <p>{message.content}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  )
}

export default App