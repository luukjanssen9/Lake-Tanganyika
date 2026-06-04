import LakeMap from "../components/LakeMap";
import PageHeader from "../components/PageHeader";

export default function MapPage() {
  return (
    <>
      <PageHeader
        eyebrow="GeoJSON layers"
        title="Lake Tanganyika basin and gauge map"
        subtitle="Basin polygons, river paths, and monitoring station points are loaded from the repository GeoJSON outputs."
      />

      <section className="map-page-grid">
        <div className="card map-card">
          <LakeMap />
        </div>
        <aside className="card explanation-card">
          <h2>Study area</h2>
          <p>
            This map shows the Lake Tanganyika study area, including contributing river basins, river paths, and available
            monitoring stations or gauges used in the analysis.
          </p>
          <p>All three layers are visible by default. Use the selectors to focus on a specific river or gauge.</p>
        </aside>
      </section>
    </>
  );
}
