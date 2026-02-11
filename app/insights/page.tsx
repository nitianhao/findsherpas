import { redirect } from "next/navigation";

/**
 * /insights redirects to /blog.
 * The nav labels it "Insights" but content lives at /blog.
 */
export default function InsightsRedirect() {
  redirect("/blog");
}
