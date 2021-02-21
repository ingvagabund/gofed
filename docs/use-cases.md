## Use cases

### Generate spec file

For a given golang project generate corresponding spec file.
User specifies project (repository-project pair or import path, commit).
A client downloads a tarball (after contructing the correct download url) or
user specifies a tarball. Client then sends the tarball to symbol extractor.
Extractor returns a data set (or its subset based on a correct extractor).
Client then sends the data to a [Specker](https://github.com/gofed/specker),
sets its output format. Specker responses with requested output format.  Client
writes output to a file.

### Regenerate spec representation

For a given spec representation (e.g. spec file) update its parts based
on a user preferences (update a list of dependencies, update to newer
commit, etc.).
User specifies a spec representation and a set of changes to apply.
Client send spec representation and set of changes to Specker.
Specker returns updated spec representation.
Client writes the returned spec representation to a file.

### Compare two commits

For two commits of the same project I would like to compare its API to see
what has changed.
User specifies a project and two commits. Client asks for API of the corresponding
commits. The data are retrieved from downloaded tarballs or from another storage.
Two sets of APIs are sent to API analyzer. Analyzer returns a difference of the APIs.
Clients writes the difference to a file.

### Check commit

For a given package name and a commit check if the package is packaged in a distribution
and the commit is out-dated, up-to-date or newer.
This is usefull when I want to package a golang project and I am not sure
if a distribution already fulfill my needs.

### Check deps

For a given list of import packages and commits check each item in the list
if it is packaged in a distribution.
This is usually done for each new release of a given project.
All items are checked and information about its state is reported.

### Inspect tarball

For a given source code tarball run various inspection/extractions and return requested metada or data (list of dependencies, list of provides, list of tests, etc.). Or generate a list of bundled deps, list of provides with epoch, etc.

### Review a spec file

For a given spec file, run analysis (lint on a spec file), request for Koji build
and generate a review request (possibly in bugzilla).
This should be fully automated. E.g. upload a srpm (spec, tarball) to a server,
server runs the review script (possibly locally) and reports if anything goes wrong or well.

### Scan deps

For all golang packages in a distribution scan dependencies among them
and return a requested resource (dependency graph, list of missing dependencies,
list of cyclic dependencies, list of unused packages, etc.).

### Scan upstream repositories

For a given upstream repository run an analysis on a list of commits (compare two commits,
differencies in API, etc.). Return a requested resource.

### Analysis of deps for a given project

Each project has non-empty set of dependencies on other projects (at least on standard golang library).
These dependencies can change over time. I would like to know how much. E.g. how many
new packages occurs, frequence of changes of commits of each imported package, etc.)

### Comparision of projects
Some projects are forked from other. Sometimes this is hard to detect by eye.
For that, I would like to run a comparisions between commits and projects to discover,
if there are projects that are very similar and can be merged into one.
This can be run on both upstream repositories and on projects packaged in a distribution.

### Spec file translator
For a given spec file I would like to modify its parts based on requested modifications.
E.g. reformat lists of deps, remove multiple empty lines, add new lines where necesary,
remove a devel subpackage (for migration between distributions and branches if reasonable).

### Multi spec file generator
For a given project I would like not to just generate a spec file for it. I would like to
generate a spec file for all its dependencies (direct and indirect). Based on a configuraiton
only projects not yet packages in a distribution can be generated. At first, a dependency
graph is constructed (based on a deps file). Then all nodes are checked and corresponding
spec files generated (if requested). If requested, only metadata can be returned or scan
run (without genereating spec files, just analysis of APIs)

### Minimize API breakage of golang projects
In a loop analysis all projects packaged in a distribution and check for API breakages.
As a result I would like to get a list of projects that have broken dependencies. I.e.
missing symbols, changed symbols (different number or type of arguments than expected), etc.

### Guided update
When updating a golang project to different commit (usually newer) a user is warned if the update
breaks other projects or at least warned there is a possible breakage.
If requested, check all [B]R, Provides, list of tests, building scripts (if implemented), etc.

### Automatically update a list of deps/provides/tests
For a given spec file and tarball, run analysis of the tarball and update a list of dependencies
of provides accordingaly. Other lists or parts of the spec file can be updated if requested.

### Generate self-standing devel subpackages
In order to minimize an amount of source code installed, a list of devel subpackage
in a spec file can be reorganized (add/remove devel subpackages).
At first a local dependency graph (project scope) is constructed. Potential devel subpackages
are detected (usually one subpackage per list and per inner node). The graph can be minized
before detection (merge strongly connected components, merge nodes (of they are not
big enough based on some node evaluation function or heuristics).

### Detection of usage of exported symbols
Each golang projects exported public symbols to by used (provided API).
Some projects use exported symbols of its dependencies.
In order to know which symbols are used and provided, all projects are analyzed.
Result is resource with a list of provided and used symbols. Other data or metadata
can be provided.

From a given data source (tarball, spec file, json, etc.) generate a spec file.

- There can be one extractor and other virtual extractors build on it that returns only a subset of extracted data. What design pattern is it? {I have one set a data and pick up only a part of it}
- Client can communicate with local libraries or send requests to server. This should be transparent to a user (just choose the correct receiver).
- Client should not be aware of spec model and manipulations with it. Responsibility of the specker is to deal with translation of spec representation to a model and manipulation with it. Client gets a list of permitted operations that can be applied on the spec representation. Each operation is abstract and requires only data that are used/required for a change.

- specker will provide a minimal set of plugins (data inputs for various formats as json, xml, specfile, ... a.k.a input parsers) that can be used to provide package specification data. Each plugin (json_parser, specfile_parser, ...) will talk to spec model writer which will create an abstract spec model. Based on a use case the model get updated (transformed based on requested changes) or renderred (to requested representation). Or constructed model can be used for various analysis (validation, statistics, metadata extraction, etc.).

- from another point of view, GoSymbolExtractor will return extracted data. Go client aware of golang specifics (specification of an abstract client) will transform the data into specker supported format (json most likely). When instantiating the specker, the client will set a language orientation. The specker will store language orientation as spec model metadata. The orientation is then used to call the correct language renderrer (if needed). Again, the abstract spec model is meant to be as assumption free as possible. Or there could be one model for each language or in general for model orientation. If this will be the case, what methods should be in model transformation API? Maybe there could be some general transformation interfaces classes and some customized classes which inherits from general/default ones.

- So there will be another repository called "go-clients" and its corresponding class which will inherit from a general class client. (thanks for pvalena for brainstorming)

- Add suport for various formats of deps file (Godeps.json, vendor, glade.yml, etc.)
- When checking for a list of deps, local database, local repositories or remote database/repositories can be used. This should be configurable and in most cases transparent to a user.
- keep snapshots of actual state of golang projects packaged in a distribution. E.g. list of provided API in a given time (or automatically store the API with each new commit/build).
- a deps file is in a tarball (or can be generated from the tarball). So this will be built over SymbolExtractor.
