import { ArrowRight, BarChart3, Database, MapPinned, Timer } from "lucide-react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { assetUrl } from "../lib/dataLoader";

const destinationCards = [
  { to: "/graphs", label: "Graphs", detail: "Browse charts for lake levels, river water levels, rainfall, temperature, NDVI, and model outputs.", icon: BarChart3 },
  { to: "/predictions", label: "Predictions", detail: "Compare observed water levels with model results and short-term forecasts.", icon: Timer },
  { to: "/map", label: "Map", detail: "Explore the lake area, river basins, station locations, and project layers.", icon: MapPinned },
  { to: "/data", label: "Data", detail: "See the main datasets used in the project, including their sources and processed files.", icon: Database },
];

const heroCredit =
  "Naph, I. (n.d.). A tranquil scene of a boat on a lake near tropical beach huts and lush greenery [Photograph]. Pexels. https://www.pexels.com/photo/serene-lake-boat-near-tropical-beach-huts-35242823/";

export default function IntroPage() {
  return (
    <>
      <PageHeader
        eyebrow="Lake Tanganyika project"
        title={<em>Lake Tanganyika, what are you doing?</em>}
        subtitle="Explore how Lake Tanganyika and nearby rivers change over time using water-level records, rainfall, temperature, satellite indicators, and model results."
        className="home-header"
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
            This dashboard brings the main project results together in one place. It connects observed lake and river measurements
            with climate data, satellite indicators, basin boundaries, station locations, and prediction outputs.
          </p>
          <p>
            The goal is to make the Lake Tanganyika data easier to explore and compare, especially for understanding water-level
            changes and possible flood risk around the lake.
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
