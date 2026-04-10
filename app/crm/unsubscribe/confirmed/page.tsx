export default function UnsubscribeConfirmedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="max-w-md text-center space-y-3 px-6">
        <h1 className="text-xl font-semibold">You&apos;ve been unsubscribed</h1>
        <p className="text-sm text-muted-foreground">
          You will no longer receive emails from this sender. If this was a mistake, please reply to any previous email.
        </p>
      </div>
    </div>
  );
}
