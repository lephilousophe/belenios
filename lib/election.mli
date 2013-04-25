(** Election primitives *)

open Signatures

val finite_field : p:Z.t -> q:Z.t -> g:Z.t ->
  (module GROUP with type t = Z.t)
(** [finite_field p q g] builds the multiplicative subgroup of F[p],
    generated by [g], of order [q]. *)

val check_finite_field : p:Z.t -> q:Z.t -> g:Z.t -> bool
(** Check consistency of finite field parameters. *)

val check_election : (module ELECTION_PARAMS) -> bool
(** Check consistency of election parameters. *)

module MakeSimpleMonad (G : GROUP) : ELECTION_MONAD
  with type ballot = G.t Serializable_t.ballot
  and type 'a t = unit -> 'a
(** Simple election monad that keeps all ballots in memory. It uses a
    secure random number generator lazily initialized by a seed shared
    by all instances. *)

module MakeElection
  (P : ELECTION_PARAMS)
  (M : ELECTION_MONAD with type ballot = P.G.t Serializable_t.ballot)
  : ELECTION
  with type elt = P.G.t
  and type 'a m = 'a M.t
