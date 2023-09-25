//const stripe = Stripe("pk_test_51NNnWHL5vg0DlJRprqAYVoEw7zReRWdapwQzYRZzADPk0pD9VenOo7L4z8opPDBIryI4VIX42CbZXFU4rFGqRZl300SGQQnEXJ");
const stripe = Stripe("pk_live_51NNnWHL5vg0DlJRpXg28qI66LyL95vOvr350dLwnaeNDdExeKfDSxL8Nnuu1iYGh6OKxDxI0w7bF39dyaMZmIK2S000eEpGcqA");

document.cookie = 'session_id' +'=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';

// Retrieve the "payment_intent_client_secret" query parameter appended to
// your return_url by Stripe.js
const clientSecret = new URLSearchParams(window.location.search).get(
  'payment_intent_client_secret'
);

// Retrieve the PaymentIntent
stripe.retrievePaymentIntent(clientSecret).then(({paymentIntent}) => {
  const message = document.querySelector('#message')

  // Inspect the PaymentIntent `status` to indicate the status of the payment
  // to your customer.
  //
  // Some payment methods will [immediately succeed or fail][0] upon
  // confirmation, while others will first enter a `processing` state.
  //
  // [0]: https://stripe.com/docs/payments/payment-methods#payment-notification

  var amount = paymentIntent.amount / 100;
  amount = amount.toString();
  var receipt_email = paymentIntent.receipt_email;

  switch (paymentIntent.status) {
    case 'succeeded':
      message.innerText = 'Success! $' + amount + ' payment received. An email confirmation will be emailed to ' + receipt_email + '.';
      break;

    case 'processing':
      message.innerText = "Payment processing. We'll update you via email at " + receipt_email + "when payment is received.";
      break;

    case 'requires_payment_method':
      message.innerText = 'Payment failed. Please try another payment method.';
      // Redirect your user back to your payment page to attempt collecting
      // payment again
      break;

    default:
      message.innerText = 'Something went wrong.';
      break;
  }
});

