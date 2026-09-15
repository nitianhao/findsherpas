"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";

export function ReachOutForm() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    message: "",
    website: "",
  });
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const statusRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === "success" || status === "error") statusRef.current?.focus();
  }, [status]);

  function handleChange(
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (status === "loading") return;
    setStatus("loading");
    setErrorMsg("");
    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
        signal: AbortSignal.timeout(20000),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        setErrorMsg(
          typeof data?.error === "string"
            ? data.error
            : "Your message could not be sent. Please try again or email us directly.",
        );
        setStatus("error");
        return;
      }
      setStatus("success");
    } catch {
      setErrorMsg(
        "We could not confirm that your message was sent. Check your connection and try again, or email michal@findsherpas.com.",
      );
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div
        ref={statusRef}
        role="status"
        tabIndex={-1}
        className="fs-form-status"
      >
        <h3>Thank you for the context.</h3>
        <p>Your message has been sent. We will be in touch at {form.email}.</p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-busy={status === "loading"}
      className="fs-form"
    >
      <input
        type="text"
        name="website"
        value={form.website}
        onChange={handleChange}
        autoComplete="off"
        tabIndex={-1}
        aria-hidden="true"
        className="fs-honeypot"
      />
      <div className="fs-form-pair">
        <div className="fs-field">
          <label htmlFor="contact-name">Name</label>
          <input
            id="contact-name"
            name="name"
            autoComplete="name"
            required
            maxLength={200}
            value={form.name}
            onChange={handleChange}
          />
        </div>
        <div className="fs-field">
          <label htmlFor="contact-email">Email</label>
          <input
            id="contact-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
            value={form.email}
            onChange={handleChange}
          />
        </div>
      </div>
      <div className="fs-field">
        <label htmlFor="contact-company">
          Store or company <span>(optional)</span>
        </label>
        <input
          id="contact-company"
          name="company"
          autoComplete="organization"
          maxLength={500}
          value={form.company}
          onChange={handleChange}
          placeholder="Your store’s name or website"
        />
      </div>
      <div className="fs-field">
        <label htmlFor="contact-message">What would you like to improve?</label>
        <textarea
          id="contact-message"
          name="message"
          required
          minLength={1}
          maxLength={10000}
          rows={6}
          value={form.message}
          onChange={handleChange}
          placeholder="A few sentences about your search and what you have in mind."
        />
      </div>
      {status === "error" && (
        <div
          ref={statusRef}
          role="alert"
          tabIndex={-1}
          className="fs-form-error"
        >
          {errorMsg}
        </div>
      )}
      <button
        type="submit"
        disabled={status === "loading"}
        className="fs-button"
      >
        {status === "loading" ? "Sending…" : "Send message"}
        <ArrowRight size={20} aria-hidden="true" />
      </button>
      <p className="fs-form-note">
        We use these details to respond to your enquiry. Please do not include
        customer records or confidential search data.
      </p>
    </form>
  );
}
