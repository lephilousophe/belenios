(**************************************************************************)
(*                                BELENIOS                                *)
(*                                                                        *)
(*  Copyright © 2022-2023 Inria, CNRS                                     *)
(*                                                                        *)
(*  This program is free software: you can redistribute it and/or modify  *)
(*  it under the terms of the GNU Affero General Public License as        *)
(*  published by the Free Software Foundation, either version 3 of the    *)
(*  License, or (at your option) any later version, with the additional   *)
(*  exemption that compiling, linking, and/or using OpenSSL is allowed.   *)
(*                                                                        *)
(*  This program is distributed in the hope that it will be useful, but   *)
(*  WITHOUT ANY WARRANTY; without even the implied warranty of            *)
(*  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU     *)
(*  Affero General Public License for more details.                       *)
(*                                                                        *)
(*  You should have received a copy of the GNU Affero General Public      *)
(*  License along with this program.  If not, see                         *)
(*  <http://www.gnu.org/licenses/>.                                       *)
(**************************************************************************)

open Belenios_api.Serializable_j
open Belenios_core.Serializable_t

type 'a t

val invalidate_all : unit -> unit
val invalidate : 'a t -> unit
val modified : 'a t -> bool
val set : 'a t -> 'a -> unit
val get : 'a t -> ('a, string) result Lwt.t
val get_until_success : 'a t -> 'a Lwt.t
val sync : unit -> (unit, string) result Lwt.t
val sync_until_success : unit -> unit Lwt.t
val config : configuration t
val draft : draft t
val voters : voter_list t
val status : draft_status t
val account : api_account t
val e_elec : params t
val e_voters : voter_list t
val e_records : records t
val e_status : election_status t
val e_dates : election_auto_dates t
