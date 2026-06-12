import assert from "node:assert/strict";
import { checkoutUrlFailures } from "./checkout-url.mjs";

assert.deepEqual(checkoutUrlFailures(""), []);
assert.deepEqual(checkoutUrlFailures("https://buy.stripe.com/test_fixture"), []);
assert.match(
  checkoutUrlFailures("http://buy.stripe.com/test_fixture").join("\n"),
  /must use https/,
);
assert.match(
  checkoutUrlFailures("https://example.com/test_fixture").join("\n"),
  /buy\.stripe\.com/,
);
assert.match(
  checkoutUrlFailures("not a url").join("\n"),
  /valid URL/,
);

console.log("Checkout URL verification tests passed.");
