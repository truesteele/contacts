# Camping Reservation Audit — Instructions for Claude

Sally, paste this entire document into a Claude conversation that has access to your Gmail (via Google Workspace MCP tools). It will search your inboxes and compile our complete camping history.

---

## Task

Search all of my Gmail accounts for camping reservation emails, extract the details from each one, and compile a complete list of camping trips. Output a table of every trip with: campground, dates, nights, status (completed / cancelled / confirmed), provider, and reservation number.

## How to Execute

### Step 1: Discover my Gmail accounts

Use the Google Workspace MCP tools available to you. Check which Gmail accounts you have access to by trying `search_gmail_messages` on each available MCP server. Search for `from:recreation.gov` as a test query on each account to confirm access.

### Step 2: Search each account

For each Gmail account, run these searches. Collect ALL results (paginate if needed):

```
from:(communications@recreation.gov)
from:(noreply@reservecalifornia.com) subject:(confirmation OR reservation OR cancellation OR cancelled)
from:(reservecalifornia@parks.ca.gov) subject:(confirmation OR reservation OR cancellation OR cancelled)
from:(AutomaticEmail@usedirect.com) subject:(confirmation OR reservation OR cancellation OR cancelled)
from:(noreply@reserveamerica.com) subject:(confirmation OR cancelled)
from:(reserveamerica@reserveamerica.com) subject:(confirmation OR cancelled)
from:(sonomacountyparks@itinio.com) subject:(reservation OR confirmation)
from:(hipcamp.com) subject:(reservation OR booking OR confirmation OR cancelled)
from:(campspot.com) subject:(reservation OR booking OR confirmation)
from:(koa@camp.koa.com) subject:(reservation OR booking OR confirmation)
from:(thousandtrails.com) subject:(reservation OR booking OR confirmation)
```

### Step 3: Fetch and parse each email

For each email found, fetch the full content and extract:

- **Reservation number** (Recreation.gov format: XXXXXXXXXX-X; ReserveCalifornia: #XXXXXXXX without the #)
- **Provider** (recreation_gov, reserve_california, reserve_america, itinio, hipcamp, koa, etc.)
- **Campground name** (the actual campground, not the loop/section)
- **Park system** (e.g., "California State Parks", "Pinnacles National Park")
- **Check-in date** and **Check-out date** (YYYY-MM-DD format)
- **Number of nights**
- **Total cost**
- **Email type**: confirmation, cancellation, modification, reminder, receipt, or refund
- **Site number** if available

### Step 4: Identify cancellations

An email is a CANCELLATION if any of these are true:
- Subject contains "cancellation" or "cancelled" or "canceled"
- Subject contains "Location Closure"
- Body contains "has been cancelled" or "has been canceled"
- Body contains "Refund Total" (NOT "Grand Total") — this is ReserveCalifornia-specific
- Body contains "Status: CANCELLED"
- Body has only negative quantities (e.g., "Quantity: -2") with no positive quantities — ReserveCalifornia-specific

An email is a MODIFICATION (not a cancellation) if:
- ReserveCalifornia: has both [Original Reservation] and [New Reservation] blocks with "Grand Total"
- Recreation.gov: a new "Reservation Confirmation" + "Refund Confirmation" arrive at the same timestamp — the confirmation has the NEW dates

**Important edge case:** A cancellation of a previously-modified reservation may still show [Original]/[New] blocks, but will have "Refund Total" instead of "Grand Total." "Refund Total" always means cancellation.

### Step 5: Reconcile into trips

Group emails by reservation number + provider. For each group:

1. **Dates**: Use the LATEST confirmation or modification email's dates (later emails supersede earlier ones)
2. **Status**:
   - If any email is a cancellation → status = "cancelled"
   - If the last email chronologically is a "Refund Confirmation" with no subsequent confirmation, AND the refund date is BEFORE the check-in date → status = "cancelled" (this is a cancellation without an explicit cancellation email)
   - If the last email is a refund but it's dated AFTER check-in → this is an early departure, keep as "completed"
   - If check-out date is in the past and not cancelled → status = "completed"
   - Otherwise → status = "confirmed" (upcoming trip)
3. **Modifications**: If multiple confirmations have different dates, the trip was modified. Note the original and final dates.
4. **Reminders**: These confirm existing bookings but don't change data. Skip them unless they're the only email for a reservation.

### Step 6: Output

Produce two outputs:

**Output 1: Summary stats**
- Total completed trips
- Total nights
- Total unique campgrounds
- Date range (first trip to latest)

**Output 2: Complete trip list as a table**

Sort by check-in date, ascending. Include ALL trips (completed, cancelled, and confirmed):

| Reservation # | Campground | Check-in | Check-out | Nights | Status | Provider | Account | Cost |
|--------------|-----------|----------|-----------|--------|--------|----------|---------|------|

For trips with multiple reservations on overlapping dates at the same campground (e.g., booking 2 campsites for the same weekend), note them as the same trip.

### Step 7: Save results

Save the complete table as a CSV file so we can merge it with Justin's camping data.

---

## Notes

- Some reservations are cancelled via the website without any cancellation email. If a reservation has only a booking confirmation (1 email) with no reminders and no cancellation, and the dates are in the past, it might be a "silent cancellation." Flag these for manual review.
- ReserveCalifornia sends reminders 10 and 4 days before arrival. Recreation.gov sends reminders at 3 months, 1 month, 7 days, and 2 days. The absence of reminders for a past trip can be a soft signal (but not definitive) that it was cancelled.
- If you find more than ~200 reservation emails, work through them in batches to avoid losing context.
- When in doubt about whether something is a cancellation or modification, include it in the output and flag it for review.
