import { type FormEvent, useMemo, useState } from 'react'

type Screen = 'form' | 'success' | 'invalid'

type GuestField = {
  id: number
  name: string
}

const WELCOME_MESSAGE =
  'Welcome! Please complete the information below for all guests included in your stay.'
const MAX_ADDITIONAL_GUESTS = 9
const FALLBACK_SUBMIT_DELAY_MS = 900
const PHONE_NUMBER_PATTERN = '^\\(\\d{3}\\) \\d{3}-\\d{4}$'

function getReservationId() {
  if (typeof window === 'undefined') {
    return ''
  }

  const [firstSegment, secondSegment] = window.location.pathname
    .split('/')
    .map((segment) => segment.trim())
    .filter(Boolean)

  if (firstSegment?.toLowerCase() !== 'form' || !secondSegment) {
    return ''
  }

  return decodeURIComponent(secondSegment)
}

function buildSubmissionPayload(
  reservationId: string,
  primaryGuest: string,
  phoneNumber: string,
  guests: GuestField[],
) {
  const submission: Record<string, string> = {
    'Reservation ID': reservationId,
    'Primary Guest Full Name': primaryGuest.trim(),
    'Phone number': phoneNumber.trim(),
  }

  for (let guestNumber = 2; guestNumber <= 10; guestNumber += 1) {
    submission[`Guest ${guestNumber} Full Name`] = ''
  }

  guests.forEach((guest, index) => {
    submission[`Guest ${index + 2} Full Name`] = guest.name.trim()
  })

  return { submission }
}

function formatPhoneNumber(value: string) {
  const digits = value.replace(/\D/g, '').slice(0, 10)

  if (!digits) {
    return ''
  }

  if (digits.length < 4) {
    return `(${digits}`
  }

  if (digits.length < 7) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3)}`
  }

  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`
}

function createGuestField(nextId: number): GuestField {
  return {
    id: nextId,
    name: '',
  }
}

function App() {
  const reservationId = useMemo(getReservationId, [])
  const initialScreen = useMemo<Screen>(() => {
    if (!reservationId) {
      return 'invalid'
    }

    return 'form'
  }, [reservationId])

  const [screen, setScreen] = useState<Screen>(initialScreen)
  const [primaryGuest, setPrimaryGuest] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [additionalGuests, setAdditionalGuests] = useState<GuestField[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [logoVisible, setLogoVisible] = useState(true)

  const totalGuests = 1 + additionalGuests.filter((guest) => guest.name.trim()).length

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setErrorMessage('')

    const payload = buildSubmissionPayload(
      reservationId,
      primaryGuest,
      phoneNumber,
      additionalGuests.filter((guest) => guest.name.trim()),
    )

    try {
      const endpoint = import.meta.env.VITE_FORM_SUBMIT_URL?.trim()

      if (!endpoint) {
        await new Promise((resolve) => {
          window.setTimeout(resolve, FALLBACK_SUBMIT_DELAY_MS)
        })
      } else {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        })

        if (!response.ok) {
          throw new Error(`Submission failed with status ${response.status}`)
        }
      }

      setScreen('success')
    } catch (error) {
      console.error(error)
      setErrorMessage(
        'We could not submit your guest information right now. Please try again in a moment.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleAddGuest() {
    setAdditionalGuests((currentGuests) => {
      if (currentGuests.length >= MAX_ADDITIONAL_GUESTS) {
        return currentGuests
      }

      const nextId =
        currentGuests.length === 0
          ? 1
          : Math.max(...currentGuests.map((guest) => guest.id)) + 1

      return [...currentGuests, createGuestField(nextId)]
    })
  }

  function handleGuestChange(id: number, name: string) {
    setAdditionalGuests((currentGuests) =>
      currentGuests.map((guest) =>
        guest.id === id
          ? {
              ...guest,
              name,
            }
          : guest,
      ),
    )
  }

  function handleGuestRemove(id: number) {
    setAdditionalGuests((currentGuests) =>
      currentGuests.filter((guest) => guest.id !== id),
    )
  }

  return (
    <main className="page-shell">
      <div className="page-decoration page-decoration-left" aria-hidden="true" />
      <div className="page-decoration page-decoration-right" aria-hidden="true" />

      <section className="registration-card">
        <header className="brand-header">
          {logoVisible ? (
            <img
              className="brand-logo"
              src="/edeva-stays-logo.png"
              alt="Edeva Stays"
              onError={() => setLogoVisible(false)}
            />
          ) : null}

          <p className="eyebrow">EDEVA STAYS</p>
          <h1>Guest Registration</h1>
          <p className="lead">
            {screen === 'invalid'
              ? "We couldn't identify the reservation associated with this link."
              : screen === 'success'
                ? 'Your guest information has been submitted successfully.'
                : WELCOME_MESSAGE}
          </p>
        </header>

        {screen === 'invalid' ? (
          <InvalidLinkScreen />
        ) : null}

        {screen === 'success' ? <SuccessScreen /> : null}

        {screen === 'form' ? (
          <form className="registration-form" onSubmit={handleSubmit}>
            <div className="field-grid">
              <label className="field-group field-group-full">
                <span>Primary Guest Full Name</span>
                <input
                  value={primaryGuest}
                  onChange={(event) => setPrimaryGuest(event.target.value)}
                  autoComplete="name"
                  placeholder="Enter the main guest's full name"
                  required
                />
              </label>

              <label className="field-group field-group-full">
                <span>Phone Number</span>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(event) =>
                    setPhoneNumber(formatPhoneNumber(event.target.value))
                  }
                  autoComplete="tel"
                  inputMode="numeric"
                  maxLength={14}
                  pattern={PHONE_NUMBER_PATTERN}
                  placeholder="(787) 555-1234"
                  title="Use the format (123) 456-7890"
                  required
                />
              </label>
            </div>

            <section className="guest-section">
              <div className="section-heading">
                <div>
                  <h2>Additional Guests</h2>
                  <p>
                    Add every guest included in the reservation so check-in goes smoothly.
                  </p>
                </div>

                <span className="guest-count">{totalGuests} guest(s) listed</span>
              </div>

              <div className="guest-list">
                {additionalGuests.length === 0 ? (
                  <div className="empty-state">
                    No additional guests added yet.
                  </div>
                ) : null}

                {additionalGuests.map((guest, index) => (
                  <div className="guest-row" key={guest.id}>
                    <label className="field-group">
                      <span>Additional Guest {index + 1}</span>
                      <input
                        value={guest.name}
                        onChange={(event) =>
                          handleGuestChange(guest.id, event.target.value)
                        }
                        placeholder="Full name"
                      />
                    </label>

                    <button
                      type="button"
                      className="secondary-action ghost-action"
                      onClick={() => handleGuestRemove(guest.id)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="button"
                className="secondary-action"
                onClick={handleAddGuest}
                disabled={additionalGuests.length >= MAX_ADDITIONAL_GUESTS}
              >
                + Add another guest
              </button>
            </section>

            {errorMessage ? <p className="form-error">{errorMessage}</p> : null}

            <button className="primary-action" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting guest information...' : 'Submit Guest Information'}
            </button>
          </form>
        ) : null}
      </section>
    </main>
  )
}

function SuccessScreen() {
  return (
    <section className="feedback-panel" aria-live="polite">
      <div className="success-mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <h2>Thank you!</h2>
      <p>We look forward to hosting you.</p>
      <p className="signature">Edeva Stays</p>
    </section>
  )
}

function InvalidLinkScreen() {
  return (
    <section className="feedback-panel">
      <div className="invalid-mark" aria-hidden="true">
        <span />
      </div>
      <h2>Invalid Registration Link</h2>
      <p>
        Please open the registration link that was provided with your reservation.
      </p>
    </section>
  )
}

export default App
