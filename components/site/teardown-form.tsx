"use client";

import { useState } from "react";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

interface FormState {
  status: "idle" | "loading" | "success" | "error";
  message: string;
}

export function TeardownForm() {
  const [formState, setFormState] = useState<FormState>({
    status: "idle",
    message: "",
  });

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormState({ status: "loading", message: "" });

    const form = event.currentTarget;
    const formData = new FormData(form);

    // Honeypot check
    if (formData.get("website")) {
      setFormState({ status: "success", message: "Thank you! We'll be in touch." });
      return;
    }

    const data = {
      store_url: formData.get("store_url"),
      email: formData.get("email"),
      name: formData.get("name"),
      problem_queries: formData.get("problem_queries"),
    };

    try {
      const response = await fetch("/api/teardown", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (!response.ok) {
        setFormState({
          status: "error",
          message: result.error || "Something went wrong. Please try again.",
        });
        return;
      }

      setFormState({
        status: "success",
        message: "Thank you! We'll review your store and send your teardown report within a few days.",
      });
      form.reset();
    } catch {
      setFormState({
        status: "error",
        message: "Could not submit your request. Please try again.",
      });
    }
  }

  if (formState.status === "success") {
    return (
      <div className="fs-teardown-success">
        <CheckCircle2 size={48} aria-hidden="true" />
        <h3>Request received.</h3>
        <p>{formState.message}</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="fs-teardown-form">
      <div className="fs-form-group">
        <label htmlFor="store_url">Your store URL</label>
        <input
          type="url"
          id="store_url"
          name="store_url"
          placeholder="https://yourstore.com"
          required
          autoComplete="url"
        />
        <span className="fs-form-hint">
          The store you want us to analyze.
        </span>
      </div>

      <div className="fs-form-group">
        <label htmlFor="email">Work email</label>
        <input
          type="email"
          id="email"
          name="email"
          placeholder="you@company.com"
          required
          autoComplete="email"
        />
        <span className="fs-form-hint">
          We'll send the teardown report here.
        </span>
      </div>

      <div className="fs-form-group">
        <label htmlFor="name">Your name</label>
        <input
          type="text"
          id="name"
          name="name"
          placeholder="Jane Smith"
          required
          autoComplete="name"
        />
      </div>

      <div className="fs-form-group">
        <label htmlFor="problem_queries">
          Searches that feel wrong on your site{" "}
          <span className="fs-form-optional">(optional)</span>
        </label>
        <textarea
          id="problem_queries"
          name="problem_queries"
          placeholder="Example: 'red wool sweater' returns synthetic sweaters&#10;'size 10 boots' shows all sizes&#10;'gift for dad' returns nothing"
          rows={4}
        />
        <span className="fs-form-hint">
          Up to three search queries that don't return what you'd expect.
          We'll include these in the analysis.
        </span>
      </div>

      {/* Honeypot */}
      <input
        type="text"
        name="website"
        style={{ position: "absolute", left: "-9999px" }}
        tabIndex={-1}
        autoComplete="off"
      />

      {formState.status === "error" && (
        <p className="fs-form-error" role="alert">
          {formState.message}
        </p>
      )}

      <button
        type="submit"
        className="fs-button"
        disabled={formState.status === "loading"}
      >
        {formState.status === "loading" ? (
          <>
            <Loader2 size={20} className="fs-spinner" aria-hidden="true" />
            Submitting...
          </>
        ) : (
          <>
            Request teardown <ArrowRight size={20} aria-hidden="true" />
          </>
        )}
      </button>
    </form>
  );
}
