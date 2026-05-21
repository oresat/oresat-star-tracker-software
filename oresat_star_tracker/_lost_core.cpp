/**
 * pybind11 entry point: monolithic estimate() wrapping vendored LOST without
 * modifying third_party/lost.
 */
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>

#include "attitude-utils.hpp"
#include "camera.hpp"
#include "decimal.hpp"
#include "io.hpp"

namespace py = pybind11;

namespace {

using lost::Camera;
using lost::Catalog;
using lost::Image;
using lost::Pipeline;
using lost::PipelineInput;
using lost::PipelineOptions;
using lost::PipelineOutput;

decimal focal_length_pixels(decimal focal_mm, decimal pixel_um) {
  return focal_mm * DECIMAL(1000.0) / pixel_um;
}

/**
 * PipelineInput backed by a copied grayscale buffer (same layout LOST
 * centroiding expects).
 */
class BufferPipelineInput final : public PipelineInput {
public:
  BufferPipelineInput(int width, int height, const std::uint8_t *pixels,
                      std::size_t nbytes, decimal focal_mm, decimal pixel_um)
      : catalog_(lost::CatalogRead()),
        camera_(focal_length_pixels(focal_mm, pixel_um), width, height) {
    if (width <= 0 || height <= 0) {
      throw std::invalid_argument("image width and height must be positive");
    }
    const std::size_t expected =
        static_cast<std::size_t>(width) * static_cast<std::size_t>(height);
    if (expected != nbytes) {
      throw std::invalid_argument(
          "buffer size must equal width * height for uint8 grayscale");
    }
    image_.width = width;
    image_.height = height;
    image_.image = new unsigned char[expected];
    std::memcpy(image_.image, pixels, expected);
  }

  ~BufferPipelineInput() override { delete[] image_.image; }

  const Image *InputImage() const override { return &image_; }
  const Camera *InputCamera() const override { return &camera_; }
  const Catalog &GetCatalog() const override { return catalog_; }

private:
  Image image_{};
  Camera camera_;
  const Catalog &catalog_;
};

PipelineOptions mission_pipeline_options() {
  PipelineOptions o;
  o.png = "";
  o.focalLength = 49; // 49
  o.pixelSize = DECIMAL(22.2);
  o.fov = 20; // 20
  o.centroidAlgo = "cog";
  o.centroidMagFilter = 5;
  o.databasePath = std::string{LOST_DB_PATH};
  o.idAlgo = "py";
  o.angularTolerance = DECIMAL(0.05);
  o.estimatedNumFalseStars = 1000;
  o.maxMismatchProb = DECIMAL(1e-4);
  o.attitudeAlgo = "dqm";
  return o;
}

py::array_t<double> nan_quaternion() {
  const double nan = std::numeric_limits<double>::quiet_NaN();
  py::array_t<double> a({4});
  auto m = a.mutable_unchecked<1>();
  for (py::ssize_t i = 0; i < 4; ++i) {
    m(i) = nan;
  }
  return a;
}

py::array_t<double>
estimate_impl(py::array_t<std::uint8_t, py::array::c_style> img) {
  py::buffer_info bi = img.request();
  if (bi.ndim != 2) {
    throw std::invalid_argument(
        "estimate expects a 2D uint8 array (grayscale, row-major)");
  }
  const int height = static_cast<int>(bi.shape[0]);
  const int width = static_cast<int>(bi.shape[1]);
  const auto *pixels = static_cast<const std::uint8_t *>(bi.ptr);
  const std::size_t nbytes =
      static_cast<std::size_t>(width) * static_cast<std::size_t>(height);

  const PipelineOptions opts = mission_pipeline_options();
  BufferPipelineInput input(width, height, pixels, nbytes, opts.focalLength,
                            opts.pixelSize);
  Pipeline pipeline = lost::SetPipeline(opts);
  PipelineOutput out = pipeline.Go(input);

  if (!out.attitude || !out.attitude->IsKnown()) {
    return nan_quaternion();
  }
  const lost::Quaternion q = out.attitude->GetQuaternion();
  py::array_t<double> a({4});
  auto m = a.mutable_unchecked<1>();
  m(0) = static_cast<double>(q.i);
  m(1) = static_cast<double>(q.j);
  m(2) = static_cast<double>(q.k);
  m(3) = static_cast<double>(q.real);
  return a;
}

} // namespace

PYBIND11_MODULE(_lost_core, m) {
  m.doc() = LOST_BSC_PATH;

#ifndef LOST_BSC_PATH
#error "LOST_BSC_PATH must be defined at compile time"
#endif
#ifndef LOST_DB_PATH
#error "LOST_DB_PATH must be defined at compile time"
#endif
  // LOST expects an environment variable to find the star catalog
  ::setenv("LOST_BSC_PATH", LOST_BSC_PATH, 0);
  m.def("estimate", &estimate_impl, py::arg("image"));
}
