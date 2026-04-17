/**
 * Updates linkedin_url for all CRM contacts based on research results.
 * Usage: npm run enrichment:update-linkedin
 */

import { adminDb } from "@/lib/crm/instant-db";

const LINKEDIN_MAP: Array<{ id: string; name: string; company: string; linkedin_url: string | null }> = [
  { id: "39dc5ebb-b77a-4ae7-b670-b8db72d20811", name: "Mickell Walker",          company: "Backcountry",  linkedin_url: "https://www.linkedin.com/in/mickell-walker-48524645/" },
  { id: "f841ace7-a6cf-4b80-9156-1f329623799c", name: "Emily Spears",             company: "Backcountry",  linkedin_url: "https://www.linkedin.com/in/emily-spears-27ab3757/" },
  { id: "b80a6968-c761-47ad-bce5-b2c9ce94ed76", name: "Martin Stolzenberger",     company: "Bergzeit",     linkedin_url: "https://www.linkedin.com/in/martin-stolzenberger-78423a127" },
  { id: "60b85fd5-8a27-40d5-8f21-61780aec25dc", name: "Philipp Koller",           company: "Bergzeit",     linkedin_url: "https://www.linkedin.com/in/philipp-koller-58a47b121" },
  { id: "1f449047-ab15-4d52-bffb-0fb39f098c39", name: "Davis Smith",              company: "Cotopaxi",     linkedin_url: "https://www.linkedin.com/in/davismsmith" },
  { id: "ce1c2d75-8309-44e4-baaa-c4b9c558646a", name: "Haley Anderson",           company: "Cotopaxi",     linkedin_url: "https://www.linkedin.com/in/haleyanderson166/" },
  { id: "05adf996-9a60-4a4d-a13f-484410986caa", name: "Chris Nance",              company: "Cotopaxi",     linkedin_url: "https://www.linkedin.com/in/chris-nance-4571b134/" },
  { id: "1b581e0e-58b4-4600-858b-ba012ff7fb8c", name: "Mattias Stening",          company: "Desenio",      linkedin_url: null },
  { id: "f5a7f4d4-c851-4a12-aa27-b6ba5d824f75", name: "Lovisa Lindfors",          company: "Desenio",      linkedin_url: "https://www.linkedin.com/in/lovisa-lindfors-759138128/" },
  { id: "6dc41d4c-d054-4698-a334-182f9d24d04b", name: "Thomas Kindler",           company: "Flaconi",      linkedin_url: "https://www.linkedin.com/in/thomas-kindler" },
  { id: "963a37d7-7f64-42f4-ba2b-7525eaee0c25", name: "Mohamed Sarwat",           company: "Flaconi",      linkedin_url: "https://www.linkedin.com/in/mohamed-sarwat-27a565131/" },
  { id: "5d24a122-4607-4d07-880c-3001819d6abb", name: "Richard Greiner",          company: "Huckberry",    linkedin_url: "https://www.linkedin.com/in/richard-greiner-77197323/" },
  { id: "5a0c3c56-1b31-46ef-a2a4-465056e71c36", name: "Kyle Martin",              company: "Huckberry",    linkedin_url: "https://www.linkedin.com/in/unmarketingmartin/" },
  { id: "28048b01-4791-4d71-af25-b04efc0a2473", name: "Kelly Boruta",             company: "Huckberry",    linkedin_url: "https://www.linkedin.com/in/kboruta/" },
  { id: "835e28ce-4f80-4afc-8314-3b7fcd2d7c37", name: "Amanda Schulman",          company: "Lyko",         linkedin_url: null },
  { id: "bec880b0-c444-4269-a18a-e080cc9f0ad3", name: "Louise Nobel",             company: "Lyko",         linkedin_url: "https://www.linkedin.com/in/louise-nobel-a1089240/" },
  { id: "191133a4-1218-40cc-afc4-62501a6e06d8", name: "Tiina Alahuhta-Kasko",    company: "Marimekko",    linkedin_url: "https://www.linkedin.com/in/tiina-alahuhta-kasko-146b1b26/" },
  { id: "bd2eb31d-e04e-4da3-8781-3b05686a849a", name: "Mari Nikitin",             company: "Marimekko",    linkedin_url: "https://www.linkedin.com/in/mari-nikitin/" },
  { id: "694c6a63-8146-43bc-a194-0897348dd129", name: "Eija Salmela",             company: "Marimekko",    linkedin_url: "https://www.linkedin.com/in/eija-salmela-543652139" },
  { id: "20e8625d-9596-4546-9c54-241b87b11195", name: "Konrad Kierklo",           company: "Miinto",       linkedin_url: "https://www.linkedin.com/in/konradkierklo/" },
  { id: "0875aff2-a354-4a86-9735-9cd1d66c48e7", name: "Jarno Vanhatapio",         company: "NA-KD",        linkedin_url: "https://www.linkedin.com/in/jarnovanhatapio" },
  { id: "3ae770b7-9c2b-4e71-bf45-b326eecc4753", name: "Erik Jonsson",             company: "NA-KD",        linkedin_url: "https://www.linkedin.com/in/erik-jonsson-17675b70" },
  { id: "31b280a7-ab2d-4d16-8a49-83d99e331f61", name: "Mathilda Hedberg",         company: "NA-KD",        linkedin_url: "https://www.linkedin.com/in/mathilda-hedberg-32b75389/" },
  { id: "849800ef-fb5d-497b-bfad-5d7415e9e26b", name: "Erika Öquist",             company: "Nordic Nest",  linkedin_url: null },
  { id: "fda6381e-3ee7-48e1-a298-b856510c4d29", name: "Caroline Bergman",         company: "Nordic Nest",  linkedin_url: "https://www.linkedin.com/in/caroline-bergman/" },
  { id: "381a6124-3891-4f0c-9b8d-5a1090b27e19", name: "Dave Perkins",             company: "Orvis",        linkedin_url: null },
  { id: "b03c74aa-4431-466d-abc7-89d12e2dabed", name: "Patricia Burke",           company: "Orvis",        linkedin_url: "https://www.linkedin.com/in/patricia-burke-07550a42/" },
  { id: "ab4fd0ef-5c75-4f35-8b7c-321d355fcaf6", name: "Carrie Keßler",            company: "Orvis",        linkedin_url: "https://www.linkedin.com/in/carrie-kessler-7646956/" },
  { id: "aa5441fd-3ac5-489e-9070-deb2b1d030da", name: "Hali Borenstein",          company: "Reformation",  linkedin_url: "https://www.linkedin.com/in/hali-borenstein-731b916" },
  { id: "62ce23a9-c7c5-40ae-a4b4-11d075dad2b9", name: "Jordan Wallace",           company: "Reformation",  linkedin_url: "https://www.linkedin.com/in/jordan-wallace-64407b74" },
  { id: "e60b94e0-c750-4275-881a-0308489435dc", name: "Stephen Hawthornthwaite",  company: "Rothy's",      linkedin_url: "https://www.linkedin.com/in/stephen-hawthornthwaite-7aa5872" },
  { id: "38c86069-edf3-4b14-a180-bb66d911fd76", name: "Jamie Gersch",             company: "Rothy's",      linkedin_url: "https://www.linkedin.com/in/jamie-gersch/" },
  { id: "64a00fe6-470c-49f2-8fb1-bc76ff848c8c", name: "Elise Davis",              company: "Rothy's",      linkedin_url: "https://www.linkedin.com/in/elise-mench/" },
  { id: "688b98be-45e5-4c06-9dc0-7df47fd2492a", name: "Julia Straus",             company: "Sweaty Betty", linkedin_url: "https://www.linkedin.com/in/julia-straus-5a98a211" },
  { id: "84791ebd-4dd7-4f74-81b3-833b6f45de17", name: "Helen Harding",            company: "Sweaty Betty", linkedin_url: "https://www.linkedin.com/in/helenjharding/" },
  { id: "8cc9ea3f-dbb5-44f3-9b58-49d5a9767050", name: "Paul Hedrick",             company: "Tecovas",      linkedin_url: "https://www.linkedin.com/in/paulhedrick" },
  { id: "848f20c4-b563-4bb6-9874-8ab9d10a7142", name: "Krista Dalton",            company: "Tecovas",      linkedin_url: "https://www.linkedin.com/in/krista-dalton-35a13036/" },
  { id: "b99a33f3-eb87-4765-b754-0cbdd5631b27", name: "Russ D",                   company: "Tecovas",      linkedin_url: null },
  { id: "8483693a-a64f-4d34-8917-b09e47ed387f", name: "Ryan Bartlett",            company: "True Classic", linkedin_url: "https://www.linkedin.com/in/rbtct/" },
  { id: "7c0688ad-8639-4625-bb69-76d8e4e4566e", name: "Andrew Winter",            company: "True Classic", linkedin_url: "https://www.linkedin.com/in/andrew-clark-winter/" },
  { id: "c332c36d-6615-485f-8f49-430615b7b381", name: "Alex Zamora",              company: "True Classic", linkedin_url: "https://www.linkedin.com/in/alex-zamora01" },
  { id: "4adec277-f312-4e16-925f-41d31310d7cf", name: "Joe Kudla",                company: "Vuori",        linkedin_url: "https://www.linkedin.com/in/joe-kudla-6551871/" },
  { id: "f0c7b418-238a-46e1-8323-5d452072b37a", name: "Jamie Fontana",            company: "Vuori",        linkedin_url: "https://www.linkedin.com/in/jamiefontana/" },
  { id: "b8d4a7ac-51a6-4354-909a-7121591b341e", name: "Chelsea Webb",             company: "Vuori",        linkedin_url: "https://www.linkedin.com/in/chelsea-webb-2080721b/" },
];

async function main() {
  console.log("\n=== UPDATE CONTACT LINKEDIN URLS ===\n");

  let updated = 0;
  let skipped = 0;

  for (const entry of LINKEDIN_MAP) {
    if (!entry.linkedin_url) {
      console.log(`SKIP (no URL found): ${entry.name} @ ${entry.company}`);
      skipped++;
      continue;
    }

    await adminDb.transact([
      adminDb.tx.contacts[entry.id].update({
        linkedin_url: entry.linkedin_url,
        updated_at: new Date().toISOString(),
      }),
    ]);

    console.log(`${entry.name} @ ${entry.company}`);
    console.log(`  ${entry.linkedin_url}\n`);
    updated++;
  }

  console.log("=== DONE ===");
  console.log(`Updated: ${updated}  |  Skipped (no URL): ${skipped}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
