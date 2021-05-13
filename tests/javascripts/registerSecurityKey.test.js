beforeAll(() => {
  window.CBOR = require('../../node_modules/cbor-js/cbor.js')
  require('../../app/assets/javascripts/registerSecurityKey.js')

  // disable console.error() so we don't see it in test output
  // you might need to comment this out to debug some failures
  jest.spyOn(console, 'error').mockImplementation(() => {})
})

afterAll(() => {
  require('./support/teardown.js')
})

describe('Register security key', () => {
  let button

  beforeEach(() => {
    document.body.innerHTML = `
      <a href="#" role="button" draggable="false" class="govuk-button govuk-button--secondary" data-module="register-security-key">
        Register a key
      </a>`

    button = document.querySelector('[data-module="register-security-key"]')
    window.GOVUK.modules.start()
  })

  test('creates a new credential and reloads', (done) => {
    // pretend window.navigator.credentials exists in test env
    // defineProperty is used as window.navigator is read-only
    Object.defineProperty(window.navigator, 'credentials', {
      value: {
        // fake PublicKeyCredential response from WebAuthn API
        // both of the nested properties are Array(Buffer) objects
        create: (options) => {
          expect(options).toEqual('options')

          return Promise.resolve({
            response: {
              attestationObject: [1, 2, 3],
              clientDataJSON: [4, 5, 6],
            }
          })
        }
      },
      // allow global property to be redefined in other tests
      writable: true,
    })

    // pretend window.location exists in test env
    // defineProperty is used as window.location is read-only
    Object.defineProperty(window, 'location', {
      // signal that the async promise chain was called
      value: { reload: () => done() },
      // allow global property to be redefined in other tests
      writable: true,
    })

    jest.spyOn(window.$, 'ajax').mockImplementation((options) => {
      // initial fetch of options from the server
      if (!options.method) {
        // options from the server are CBOR-encoded
        webauthnOptions = window.CBOR.encode('options')
        return Promise.resolve(webauthnOptions)

      // subsequent POST of credential data to server
      } else {
        decodedData = window.CBOR.decode(options.data)
        expect(decodedData.clientDataJSON).toEqual(new Uint8Array([4,5,6]))
        expect(decodedData.attestationObject).toEqual(new Uint8Array([1,2,3]))
        expect(options.headers['X-CSRFToken']).toBe()
        return Promise.resolve()
      }
    })

    button.click()
  })

  test('alerts if fetching WebAuthn options fails', (done) => {
    jest.spyOn(window.$, 'ajax').mockImplementation((options) => {
      return Promise.reject('error')
    })

    jest.spyOn(window, 'alert').mockImplementation((msg) => {
      done()
      expect(msg).toEqual('Error during registration. Please try again.')
    })

    button.click()
  })

  test('alerts if sending WebAuthn credentials fails', (done) => {
    Object.defineProperty(window.navigator, 'credentials', {
      value: {
        // fake PublicKeyCredential response from WebAuthn API
        create: (options) => {
          return Promise.resolve({ response: {} })
        }
      },
      // allow global property to be redefined in other tests
      writable: true,
    })

    jest.spyOn(window.$, 'ajax').mockImplementation((options) => {
      // initial fetch of options from the server
      if (!options.method) {
        webauthnOptions = window.CBOR.encode('options')
        return Promise.resolve(webauthnOptions)

      // subsequent POST of credential data to server
      } else {
        return Promise.reject('error')
      }
    })

    jest.spyOn(window, 'alert').mockImplementation((msg) => {
      done()
      expect(msg).toEqual('Error during registration. Please try again.')
    })

    button.click()
  })

  test('alerts if comms with the authenticator fails', (done) => {
    Object.defineProperty(window.navigator, 'credentials', {
      value: {
        create: () => {
          return Promise.reject(new DOMException('error'))
        }
      },
      // allow global property to be redefined in other tests
      writable: true,
    })

    jest.spyOn(window.$, 'ajax').mockImplementation((options) => {
      // initial fetch of options from the server
      webauthnOptions = window.CBOR.encode('options')
      return Promise.resolve(webauthnOptions)
    })

    jest.spyOn(window, 'alert').mockImplementation((msg) => {
      done()
      expect(msg).toEqual('Error communicating with device.\n\nerror')
    })

    button.click()
  })
})
