// DEV:
//const stripe = Stripe("pk_test_51M9UNULZJMPC73VNrRQlA8tpL189HXupEgB5TrkLSvUqWqBKtKowbBkDCAhq8w9bZz9vVnp6ZHSEY72acHlA0310007PALvgBC");
// PROD:
const stripe = Stripe("pk_live_51M9UNULZJMPC73VNhe30nkcTsYV4or05Vudl3ie1SzX6lkJsRRxHm0Z6cOzhHzvd2OGvoPxP8OzJwQ42jdDwHaFa00GkGa9kDa");

console.log(stripe);

var items = {}

// set variables that are common to both events and registration:
var common_field_names = ["event_title", "event_date", "total_cost", "customer_name", "customer_phone", "guest_quantity"];
for (let i = 0; i < common_field_names.length; i++) {
  let field_name = common_field_names[i];
  try {
    items[field_name] = document.getElementById(field_name).innerHTML;
  } catch(err) {
    console.log(err.message);
  }
}

if (items["event_title"].includes("Art Camp Registration")) {
  // set registration-related variables:
  var reg_field_names = ["camper1_name", "camper2_name", "camper3_name", "camper1_age", "camper2_age", "camper3_age", 
    "parent_address", "parent_city", "parent_state", "parent_zip", "parent_em_name", "parent_em_phone", "pickup1_name", 
    "pickup1_phone", "pickup2_name", "pickup2_phone", "session_detail"];
  for (let i = 0; i < reg_field_names.length; i++) {
    let field_name = reg_field_names[i];
    try {
      items[field_name] = document.getElementById(field_name).innerHTML;
    } catch(err) {
      console.log(err.message);
    }
  }
} else {
  if (items["event_title"].includes("After School Pottery")) {
    var field_names = ["multiple_events_details"];
  } else {
    var field_names = ["event_id", "variable_price", "additional_scarf"];
  }
  for (let i = 0; i < field_names.length; i++) {
    let field_name = field_names[i];
    try {
      items[field_name] = document.getElementById(field_name).innerHTML;
    } catch(err) {
      console.log(err.message);
    }
  }
}

let elements;

initialize();
checkStatus();

document
  .querySelector("#payment-form")
  .addEventListener("submit", handleSubmit);

let emailAddress = '';
// Fetches a payment intent and captures the client secret
async function initialize() {
  const response = await fetch("/checkout/create-payment-intent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  const { clientSecret } = await response.json();

  const appearance = {
    theme: 'stripe',
  };
  elements = stripe.elements({ appearance, clientSecret });

  const linkAuthenticationElement = elements.create("linkAuthentication");
  linkAuthenticationElement.mount("#link-authentication-element");

  linkAuthenticationElement.on('change', (event) => {
    emailAddress = event.value.email;
  });

  const paymentElementOptions = {
    layout: "tabs",
  };

  const paymentElement = elements.create("payment", paymentElementOptions);
  paymentElement.mount("#payment-element");
}

async function handleSubmit(e) {
  e.preventDefault();
  setLoading(true);

  const { error } = await stripe.confirmPayment({
    elements,
    confirmParams: {
      // Make sure to change this to your payment completion page
      return_url: "https://www.catalystcreativearts.com/checkout/",
      receipt_email: emailAddress,
    },
  });

  // This point will only be reached if there is an immediate error when
  // confirming the payment. Otherwise, your customer will be redirected to
  // your `return_url`. For some payment methods like iDEAL, your customer will
  // be redirected to an intermediate site first to authorize the payment, then
  // redirected to the `return_url`.
  if (error.type === "card_error" || error.type === "validation_error") {
    showMessage(error.message);
  } else {
    showMessage("An unexpected error occurred.");
  }

  setLoading(false);
}

// Fetches the payment intent status after payment submission
async function checkStatus() {
  const clientSecret = new URLSearchParams(window.location.search).get(
    "payment_intent_client_secret"
  );

  if (!clientSecret) {
    return;
  }

  const { paymentIntent } = await stripe.retrievePaymentIntent(clientSecret);

  switch (paymentIntent.status) {
    case "succeeded":
      showMessage("Payment succeeded!");
      break;
    case "processing":
      showMessage("Your payment is processing.");
      break;
    case "requires_payment_method":
      showMessage("Your payment was not successful, please try again.");
      break;
    default:
      showMessage("Something went wrong.");
      break;
  }
}

// ------- UI helpers -------

function showMessage(messageText) {
  const messageContainer = document.querySelector("#payment-message");

  messageContainer.classList.remove("hidden");
  messageContainer.textContent = messageText;

  setTimeout(function () {
    messageContainer.classList.add("hidden");
    messageText.textContent = "";
  }, 4000);
}

// Show a spinner on payment submission
function setLoading(isLoading) {
  if (isLoading) {
    // Disable the button and show a spinner
    document.querySelector("#submit").disabled = true;
    document.querySelector("#spinner").classList.remove("hidden");
    document.querySelector("#button-text").classList.add("hidden");
  } else {
    document.querySelector("#submit").disabled = false;
    document.querySelector("#spinner").classList.add("hidden");
    document.querySelector("#button-text").classList.remove("hidden");
  }
}
