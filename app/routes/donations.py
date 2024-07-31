from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.forms import DonationForm
from app import paypalrestsdk

donations = Blueprint('donations', __name__)

@donations.route('/donate', methods=['GET', 'POST'])
def donate():
    form = DonationForm()
    if form.validate_on_submit():
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": url_for('donations.donation_success', _external=True),
                "cancel_url": url_for('donations.donation_cancel', _external=True)
            },
            "transactions": [{
                "amount": {
                    "total": str(form.amount.data),
                    "currency": "USD"
                },
                "description": "Donation to Biodiversity Nexus"
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            flash('An error occurred during the payment process. Please try again.', 'danger')

    return render_template('donate.html', title='Donate', form=form)

@donations.route('/donation_success')
def donation_success():
    flash('Thank you for your donation!', 'success')
    return render_template('donation_success.html', title='Donation Success')

@donations.route('/donation_cancel')
def donation_cancel():
    flash('Your donation was canceled.', 'warning')
    return render_template('donation_cancel.html', title='Donation Canceled')