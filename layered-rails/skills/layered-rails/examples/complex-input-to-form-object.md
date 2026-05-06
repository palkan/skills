# Form Object for Complex Input

Replace a controller orchestrating multiple models with a form object that owns the registration workflow.

## Contents

- Before (fat controller)
- After (form object)

## Before

```ruby
class RegistrationsController < ApplicationController
  def create
    @user = User.new(user_params)
    @user.profile = Profile.new(profile_params)

    if @user.email.end_with?("@company.com")
      @user.role = :employee
      @user.team = Team.find_by(department: profile_params[:department])
    end

    if @user.save
      UserMailer.welcome(@user).deliver_later
      redirect_to dashboard_path
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def user_params
    params.require(:user).permit(:email, :password, :name)
  end

  def profile_params
    params.require(:profile).permit(:bio, :department, :avatar)
  end
end
```

## After

```ruby
# app/forms/registration_form.rb
class RegistrationForm < ApplicationForm
  attribute :email, :string
  attribute :password, :string
  attribute :name, :string
  attribute :bio, :string
  attribute :department, :string
  attribute :avatar

  validates :email, :password, :name, presence: true
  validates :email, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, length: { minimum: 8 }

  def save
    return false unless valid?

    ApplicationRecord.transaction do
      create_user
      create_profile
      assign_team if company_email?
    end

    true
  rescue ActiveRecord::RecordInvalid => e
    errors.merge!(e.record.errors)
    false
  end

  attr_reader :user

  private

  def create_user
    @user = User.create!(
      email: email,
      password: password,
      name: name,
      role: company_email? ? :employee : :member
    )
  end

  def create_profile
    @user.create_profile!(bio: bio, department: department, avatar: avatar)
  end

  def assign_team
    @user.update!(team: Team.find_by(department: department))
  end

  def company_email?
    email.end_with?("@company.com")
  end
end

# app/controllers/registrations_controller.rb
class RegistrationsController < ApplicationController
  def create
    @form = RegistrationForm.new(registration_params)

    if @form.save
      UserMailer.welcome(@form.user).deliver_later
      redirect_to dashboard_path
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def registration_params
    params.require(:registration).permit(:email, :password, :name, :bio, :department, :avatar)
  end
end
```
