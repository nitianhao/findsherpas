import { createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Privacy",
  description: "How Find Sherpas handles contact details, booking information and optional website analytics.",
  path: "/privacy",
});

export default function PrivacyPage() {
  return (
    <article className="fs-article fs-privacy">
      <h1>Privacy</h1>
      <p className="fs-privacy-updated">Last updated 14 September 2026</p>

      <p>
        This notice explains what information Find Sherpas handles when you use
        this website, contact us or book a conversation.
      </p>

      <h2>Information you choose to send</h2>
      <p>
        The contact form asks for your name, email address, message and,
        optionally, your company. We use that information to respond to your
        enquiry and to continue the conversation you requested. Form submissions
        are delivered by email using Resend.
      </p>

      <h2>Optional website analytics</h2>
      <p>
        Google Analytics is disabled until you choose “Allow analytics” in the
        notice on this site. If allowed, it helps us understand visits and usage
        patterns, such as pages viewed and general device or location
        information. Google describes the information it collects and the
        controls it provides in its{` `}
        <a href="https://support.google.com/analytics/answer/11593727?hl=en">Analytics documentation</a>.
      </p>
      <p>
        Your choice is stored in your browser. Use “Analytics settings” in the
        footer at any time to review or change it.
      </p>

      <h2>Booking a call</h2>
      <p>
        The booking link opens Cal.com, which handles the information you enter
        there under its own{` `}
        <a href="https://cal.com/privacy">privacy policy</a>.
      </p>

      <h2>How long information is kept</h2>
      <p>
        Enquiry information is kept only for as long as it is needed to respond,
        manage a potential or active working relationship, and meet applicable
        business or legal obligations.
      </p>

      <h2>Your questions and choices</h2>
      <p>
        To ask what personal information we hold about you, request a correction
        or deletion, or raise a privacy question, email{` `}
        <a href="mailto:michal@findsherpas.com">michal@findsherpas.com</a>.
      </p>
    </article>
  );
}
