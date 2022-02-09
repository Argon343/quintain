import setuptools

setuptools.setup(
    name="quintain",
    version="0.1.0",
    author="Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
)
