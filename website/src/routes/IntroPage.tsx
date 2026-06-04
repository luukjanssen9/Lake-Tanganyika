import { ArrowRight, BarChart3, Database, MapPinned, Timer } from "lucide-react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { assetUrl } from "../lib/dataLoader";

const destinationCards = [
  { to: "/graphs", label: "Graphs", detail: "Interactive lake, river, climate, NDVI, JRC, and ARIMA views.", icon: BarChart3 },
  { to: "/predictions", label: "Predictions", detail: "Compare observed and predicted lake levels across forecast horizons.", icon: Timer },
  { to: "/map", label: "Map", detail: "Framed GeoJSON basin, river, and station layers with selectors.", icon: MapPinned },
  { to: "/data", label: "Data", detail: "Readable overview of the lake, river, satellite, climate, and model datasets.", icon: Database },
];

export default function IntroPage() {
  return (
    <>
      <PageHeader
        eyebrow="Lake Tanganyika project"
        title="Lake Tanganyika water level and flood-risk prediction dashboard"
        subtitle="This dashboard combines lake, river, basin, satellite, climate, and model-prediction data to analyse and predict water-level changes around Lake Tanganyika."
      />

      <section className="intro-grid">
        <Link to="/map" className="map-preview-card">
          <img src={assetUrl("/images/maps/full-basin.png")} alt="Lake Tanganyika basin overview" />
          <span>
            Open map
            <ArrowRight size={18} aria-hidden="true" />
          </span>
        </Link>

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
