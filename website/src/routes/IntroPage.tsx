import { ArrowRight, BarChart3, Database, MapPinned, Timer } from "lucide-react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { assetUrl } from "../lib/dataLoader";

const destinationCards = [
  { to: "/graphs", label: "Graphs", detail: "Interactive lake, climate, remote-sensing, and processing views.", icon: BarChart3 },
  { to: "/predictions", label: "Predictions", detail: "Compare observed and predicted lake levels across forecast horizons.", icon: Timer },
  { to: "/map", label: "Map", detail: "Framed GeoJSON basin, river, and station layers with selectors.", icon: MapPinned },
  { to: "/data", label: "Data", detail: "Readable overview of the lake, river, satellite, climate, and model datasets.", icon: Database },
];

const heroCredit =
  "Naph, I. (n.d.). A tranquil scene of a boat on a lake near tropical beach huts and lush greenery [Photograph]. Pexels. https://www.pexels.com/photo/serene-lake-boat-near-tropical-beach-huts-35242823/";

export default function IntroPage() {
  return (
    <>
      <PageHeader
        eyebrow="Lake Tanganyika project"
        title="Lake Tanganyika water level and flood-risk prediction dashboard"
        subtitle="This dashboard combines lake, river, basin, satellite, climate, and model-prediction data to analyse and predict water-level changes around Lake Tanganyika."
      />

      <section className="intro-grid">
        <figure className="intro-visual">
          <Link to="/map" className="map-preview-card">
            <img
              src={assetUrl("/images/hero/lake-tanganyika-pexels-isaac-naph.jpg")}
              alt="Boat on Lake Tanganyika near tropical beach huts and lush greenery"
            />
            <span>
              Open map
              <ArrowRight size={18} aria-hidden="true" />
            </span>
          </Link>
          <figcaption>
            <a href="https://www.pexels.com/photo/serene-lake-boat-near-tropical-beach-huts-35242823/" target="_blank" rel="noreferrer">
              {heroCredit}
            </a>
          </figcaption>
        </figure>

        <div className="intro-side-panel">
          <p>
            The project brings together observed lake levels, river and basin geometry, gauge locations, satellite indicators,
            climate variables, and model prediction outputs into one browsable results site.
          </p>
          <div className="destination-grid">
          {destinationCards.map(({ to, label, detail, icon: Icon }) => (
            <Link key={to} to={to} className="destination-card">
              <span className="destination-card__icon">
                <Icon size={22} aria-hidden="true" />
              </span>
              <strong>{label}</strong>
              <p>{detail}</p>
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
          ))}
          </div>
        </div>
      </section>
    </>
  );
}
