// The monsters. Pure data, safe for client code.
//
// Every line has three forms. Starters are picked on the Dex page; every other
// line lives in one course and is caught by finishing a chapter of it.
// Sprites are generated from `art` by sprite.ts, coloured by `type` (body)
// and `art.part` (ears, wings, horns...).

export const TYPES = ["code", "data", "chart", "stats", "model", "neural", "lingo", "ops"] as const;
export type MonsterType = (typeof TYPES)[number];

export const TYPE_LABEL: Record<MonsterType, string> = {
  code: "Code",
  data: "Data",
  chart: "Chart",
  stats: "Stats",
  model: "Model",
  neural: "Neural",
  lingo: "Lingo",
  ops: "Ops",
};

export type Art = {
  build: "blob" | "biped" | "quad" | "bird" | "serpent";
  ears?: "pointy" | "long" | "round" | "gills" | "horns" | "antenna" | "fin" | "leaf" | "crest";
  tail?: "short" | "long" | "fluffy" | "tentacles";
  /** Form (1-3) at which wings appear. */
  wings?: 1 | 2 | 3;
  shell?: boolean;
  pattern?: "belly" | "spots" | "stripes" | "mask";
  face?: "beak" | "snout" | "fangs" | "smile";
  /** The final form grows spikes on its head. */
  spikes?: boolean;
  part: MonsterType;
};

export type Form = { name: string; dex: string };

export type MonsterLine = {
  id: string;
  type: MonsterType;
  /** Course whose chapters it is caught in. Starters have none. */
  course?: string;
  starter?: boolean;
  forms: [Form, Form, Form];
  art: Art;
};

export const ROSTER: MonsterLine[] = [
  // Starters
  {
    id: "pybble",
    type: "code",
    starter: true,
    art: { build: "serpent", ears: "fin", face: "fangs", pattern: "belly", spikes: true, part: "chart" },
    forms: [
      { name: "Pybble", dex: "Hatches curled in a nest exactly four spaces wide. Hisses at tabs." },
      { name: "Serpyth", dex: "Sheds its skin every release, and keeps the old one around for backwards compatibility." },
      { name: "Pythogon", dex: "Its hood unrolls into a scroll of nineteen aphorisms. Beautiful is better than ugly, it insists." },
    ],
  },
  {
    id: "tabbit",
    type: "data",
    starter: true,
    art: { build: "biped", ears: "long", tail: "fluffy", face: "snout", pattern: "belly", part: "stats" },
    forms: [
      { name: "Tabbit", dex: "Its long ears are column headers. It twitches them to sort." },
      { name: "Rowhare", dex: "Hops across a million rows before breakfast and never loses its index." },
      { name: "Lagomatrix", dex: "Its fur grows in a perfect grid. Every cell holds a value, and none of them are NaN." },
    ],
  },
  {
    id: "plotl",
    type: "chart",
    starter: true,
    art: { build: "biped", ears: "gills", tail: "long", face: "smile", pattern: "spots", part: "neural" },
    forms: [
      { name: "Plotl", dex: "Smiles at every scatter plot. Its gills ripple when it spots a trend." },
      { name: "Axelotl", dex: "Regrows any axis it loses, and prefers them labelled." },
      { name: "Gridlotl", dex: "Rules the subplot grid. Redraws a chart until every colour passes contrast." },
    ],
  },

  // Data Science & Machine Learning track
  {
    id: "loopip",
    type: "code",
    course: "python-for-data-science",
    art: { build: "bird", ears: "crest", wings: 1, face: "beak", pattern: "belly", part: "chart" },
    forms: [
      { name: "Loopip", dex: "Runs in circles until someone tells it to break." },
      { name: "Iterwing", dex: "Flies through a list one item at a time and never skips a step." },
      { name: "Recursoar", dex: "Soars in ever-smaller spirals until it reaches its base case, then returns home." },
    ],
  },
  {
    id: "pandling",
    type: "data",
    course: "pandas-data-manipulation",
    art: { build: "blob", ears: "round", face: "snout", pattern: "mask", part: "ops" },
    forms: [
      { name: "Pandling", dex: "Chews through messy CSVs like bamboo and leaves tidy data behind." },
      { name: "Groupanda", dex: "Sorts everything it finds into groups, then insists on aggregating them." },
      { name: "Pivotitan", dex: "Turns any table on its side with one paw. Reshapes the forest to suit its index." },
    ],
  },
  {
    id: "barkit",
    type: "chart",
    course: "data-visualization",
    art: { build: "quad", ears: "pointy", tail: "short", face: "snout", pattern: "spots", part: "data" },
    forms: [
      { name: "Barkit", dex: "Barks once per category. Bigger counts get taller barks." },
      { name: "Scatterhound", dex: "Its spots are data points. It sniffs out an outlier from a mile away." },
      { name: "Histogrowl", dex: "Growls in bins. Narrow the bin width and it only gets louder." },
    ],
  },
  {
    id: "dicekin",
    type: "stats",
    course: "statistics-probability",
    art: { build: "blob", ears: "antenna", face: "smile", pattern: "spots", spikes: true, part: "code" },
    forms: [
      { name: "Dicekin", dex: "Rolls everywhere. Nobody knows which face will land on top, least of all Dicekin." },
      { name: "Bayesprite", dex: "Updates its mood with every new observation. Starts each day with a mild prior." },
      { name: "Gaussquatch", dex: "Rarely seen more than three standard deviations from its den. Bell-shaped when asleep." },
    ],
  },
  {
    id: "labelamb",
    type: "model",
    course: "supervised-learning",
    art: { build: "quad", ears: "horns", face: "snout", pattern: "belly", part: "chart" },
    forms: [
      { name: "Labelamb", dex: "Follows whoever holds the answer key. Learns fast, as long as every example is labelled." },
      { name: "Ramgressor", dex: "Charges straight down the slope of any loss curve." },
      { name: "Gradiaries", dex: "Its horns curl in the shape of a decision boundary. Always holds out a validation set." },
    ],
  },
  {
    id: "blobble",
    type: "model",
    course: "unsupervised-learning",
    art: { build: "blob", shell: true, face: "smile", pattern: "spots", part: "lingo" },
    forms: [
      { name: "Blobble", dex: "Drifts until it bumps into blobs like itself, then sticks to them." },
      { name: "Clusterclam", dex: "Snaps shut around groups of similar pearls. Picks k by feel." },
      { name: "Centroidon", dex: "Everything nearby ends up orbiting it. It only moves to stay at their mean." },
    ],
  },
  {
    id: "scalet",
    type: "model",
    course: "feature-engineering-evaluation",
    art: { build: "quad", tail: "long", face: "fangs", pattern: "stripes", spikes: true, part: "code" },
    forms: [
      { name: "Scalet", dex: "Shrinks or stretches itself until every feature sits between zero and one." },
      { name: "Encodile", dex: "Swallows categories whole and spits out one-hot vectors." },
      { name: "Crossvalgator", dex: "Splits its prey into k folds and tests each one. Nothing leaks past its jaws." },
    ],
  },
  {
    id: "splitling",
    type: "model",
    course: "tree-ensembles",
    art: { build: "biped", ears: "leaf", face: "smile", pattern: "stripes", part: "code" },
    forms: [
      { name: "Splitling", dex: "Asks one yes-or-no question a day and grows a branch for each answer." },
      { name: "Baggroot", dex: "Grows from a random handful of seeds. The whole grove votes on every decision." },
      { name: "XGBoak", dex: "Each ring corrects the mistakes of the ring before it. Wins most tabular tournaments." },
    ],
  },

  // AI Engineering track
  {
    id: "neurite",
    type: "neural",
    course: "deep-learning-pytorch",
    art: { build: "biped", ears: "crest", tail: "long", wings: 3, face: "fangs", spikes: true, part: "lingo" },
    forms: [
      { name: "Neurite", dex: "Fires a tiny spark whenever something interesting passes by." },
      { name: "Tensaur", dex: "Stacks its memories in tensors along its back. Prefers to run on a GPU." },
      { name: "Backpropteryx", dex: "Flies forward, then glides back over its own path, nudging every feather by its gradient." },
    ],
  },
  {
    id: "tokit",
    type: "neural",
    course: "nlp-transformers",
    art: { build: "bird", ears: "antenna", wings: 1, face: "smile", pattern: "spots", part: "stats" },
    forms: [
      { name: "Tokit", dex: "Nibbles sentences into subword crumbs and leaves ##ing everywhere." },
      { name: "Attendril", dex: "Every eye on its wings watches a different word, all at once." },
      { name: "Transformoth", dex: "Drawn to context the way other moths are drawn to light." },
    ],
  },
  {
    id: "chirpt",
    type: "lingo",
    course: "llm-apis-prompting",
    art: { build: "bird", ears: "crest", wings: 1, face: "beak", pattern: "belly", part: "chart" },
    forms: [
      { name: "Chirpt", dex: "Repeats whatever you tell it, only slightly more politely." },
      { name: "Parrompt", dex: "Does its best work when you say exactly what you want, with an example or two." },
      { name: "Contextcaw", dex: "Remembers every word of the conversation, and charges for each one." },
    ],
  },
  {
    id: "vecto",
    type: "lingo",
    course: "embeddings-vector-search",
    art: { build: "blob", ears: "antenna", shell: true, face: "smile", pattern: "belly", part: "stats" },
    forms: [
      { name: "Vecto", dex: "Points in a direction only it understands. Usually toward food." },
      { name: "Cosnail", dex: "Measures how alike two things are by the angle between them. Slow, but very accurate." },
      { name: "Embedilus", dex: "Its spiral shell has a thousand dimensions. Similar memories sit in neighbouring chambers." },
    ],
  },
  {
    id: "ragpup",
    type: "lingo",
    course: "rag-systems",
    art: { build: "quad", ears: "pointy", tail: "fluffy", face: "snout", pattern: "mask", part: "data" },
    forms: [
      { name: "Ragpup", dex: "Fetches anything you throw. Sometimes the wrong stick, but always with a citation." },
      { name: "Retrievolf", dex: "Hunts in packs of top-k and tracks the scent of a relevant chunk for miles." },
      { name: "Ragnaroar", dex: "Answers only from what it can find. Its roar ends every hallucination." },
    ],
  },
  {
    id: "antool",
    type: "ops",
    course: "agents-tool-use",
    art: { build: "biped", ears: "antenna", face: "fangs", pattern: "stripes", part: "chart" },
    forms: [
      { name: "Antool", dex: "Carries a tool many times its size and knows exactly when to use it." },
      { name: "Plannant", dex: "Thinks three steps ahead, then checks its work after each one." },
      { name: "Orchestrant", dex: "Directs a colony of sub-agents. Each one reports back before it moves on." },
    ],
  },
  {
    id: "hootest",
    type: "stats",
    course: "llm-evaluation",
    art: { build: "bird", ears: "pointy", wings: 2, face: "beak", pattern: "belly", part: "lingo" },
    forms: [
      { name: "Hootest", dex: "Asks \"who?\" about every answer. Mostly: who said this was correct?" },
      { name: "Benchowl", dex: "Perches on leaderboards and squints at the test set for leaks." },
      { name: "Arbitowl", dex: "A strict but fair judge. Its rubric is written on the inside of its wings." },
    ],
  },
  {
    id: "pipsquid",
    type: "ops",
    course: "mlops-model-serving",
    art: { build: "blob", ears: "fin", tail: "tentacles", face: "smile", pattern: "spots", part: "data" },
    forms: [
      { name: "Pipsquid", dex: "Lives in a requirements file. Pins every version, just in case." },
      { name: "Dockalamari", dex: "Packs itself into a container and behaves the same wherever it washes up." },
      { name: "Kraken8s", dex: "Its tentacles scale out to meet demand, then retract when the traffic calms down." },
    ],
  },
];

export const STARTERS = ROSTER.filter((l) => l.starter);

export function getLine(id: string): MonsterLine | undefined {
  return ROSTER.find((l) => l.id === id);
}

export function lineForCourse(courseSlug: string): MonsterLine | undefined {
  return ROSTER.find((l) => l.course === courseSlug);
}
