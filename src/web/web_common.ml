(**************************************************************************)
(*                                BELENIOS                                *)
(*                                                                        *)
(*  Copyright © 2012-2014 Inria                                           *)
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

open Lwt
open Platform
open Signatures
open Common
open Serializable_builtin_t
open Serializable_builtin_j
open Serializable_t
open Web_serializable_t

let enforce_single_element s =
  let open Lwt_stream in
  lwt t = next s in
  lwt b = is_empty s in
  (assert_lwt b) >>
  Lwt.return t

let load_from_file read fname =
  let i = open_in fname in
  let buf = Lexing.from_channel i in
  let lex = Yojson.init_lexer ~fname () in
  let result = read lex buf in
  close_in i;
  result

let make_rng = Lwt_preemptive.detach (fun () ->
  pseudo_rng (random_string secure_rng 16)
)

module type LWT_RANDOM = Signatures.RANDOM with type 'a t = 'a Lwt.t

module type LWT_RNG = sig
  val rng : rng Lwt.t
end

module MakeLwtRandom (X : LWT_RNG) = struct

  type 'a t = 'a Lwt.t
  let return = Lwt.return
  let bind = Lwt.bind
  let fail = Lwt.fail

  let random q =
    let size = Z.bit_length q / 8 + 1 in
    lwt rng = X.rng in
    let r = random_string rng size in
    return Z.(of_bits r mod q)

end

type error =
  | Serialization of exn
  | ProofCheck
  | ElectionClosed
  | MissingCredential
  | InvalidCredential
  | RevoteNotAllowed
  | ReusedCredential
  | WrongCredential
  | UsedCredential
  | CredentialNotFound

exception Error of error

let fail e = Lwt.fail (Error e)

let explain_error = function
  | Serialization e ->
    Printf.sprintf "your ballot has a syntax error (%s)" (Printexc.to_string e)
  | ProofCheck -> "some proofs failed verification"
  | ElectionClosed -> "the election is closed"
  | MissingCredential -> "a credential is missing"
  | InvalidCredential -> "your credential is invalid"
  | RevoteNotAllowed -> "you are not allowed to revote"
  | ReusedCredential -> "your credential has already been used"
  | WrongCredential -> "you are not allowed to vote with this credential"
  | UsedCredential -> "the credential has already been used"
  | CredentialNotFound -> "the credential has not been found"

let security_logfile = ref None

let open_security_log f =
  lwt () =
    match !security_logfile with
      | Some ic -> Lwt_io.close ic
      | None -> return ()
  in
  lwt ic = Lwt_io.(
    open_file ~flags:Unix.(
      [O_WRONLY; O_APPEND; O_CREAT]
    ) ~perm:0o600 ~mode:output f
  ) in
  security_logfile := Some ic;
  return ()

let security_log s =
  match !security_logfile with
    | None -> return ()
    | Some ic -> Lwt_io.atomic (fun ic ->
      Lwt_io.write ic (
        string_of_datetime (now ())
      ) >>
      Lwt_io.write ic ": " >>
      Lwt_io.write_line ic (s ()) >>
      Lwt_io.flush ic
    ) ic

let fail_http status =
  raise_lwt (
    Ocsigen_extensions.Ocsigen_http_error
      (Ocsigen_cookies.empty_cookieset, status)
  )

let forbidden () = fail_http 403

let rewrite_fun = ref (fun x -> x)

let rewrite_prefix x = !rewrite_fun x

let set_rewrite_prefix ~src ~dst =
  let nsrc = String.length src in
  let f x =
    let n = String.length x in
    if n >= nsrc && String.sub x 0 nsrc = src then
      dst ^ String.sub x nsrc (n-nsrc)
    else x
  in rewrite_fun := f

let empty_metadata = {
  e_voting_starts_at = None;
  e_voting_ends_at = None;
  e_readers = None;
  e_voters = None;
  e_owner = None;
  e_auth_config = None;
}

let check_acl a u =
  match a with
  | Some `Any -> true
  | Some (`Many items) ->
    let rec loop = function
      | [] -> false
      | item :: _ when item.acl_domain = u.user_domain ->
        (match item.acl_users with
        | `Any -> true
        | `Many users -> SSet.mem u.user_name users
        )
      | _ :: xs -> loop xs
    in loop items
  | _ -> false

let uuid = Eliom_parameter.user_type
  ~of_string:(fun x -> match Uuidm.of_string x with
    | Some x -> x
    | None -> invalid_arg "uuid")
  ~to_string:Uuidm.to_string

type election_file =
  | ESRaw
  | ESKeys
  | ESCreds
  | ESBallots
  | ESRecords
  | ESETally

let election_file_of_string = function
  | "election.json" -> ESRaw
  | "public_keys.jsons" -> ESKeys
  | "public_creds.txt" -> ESCreds
  | "ballots.jsons" -> ESBallots
  | "records" -> ESRecords
  | "encrypted_tally.json" -> ESETally
  | x -> invalid_arg ("election_dir_item: " ^ x)

let string_of_election_file = function
  | ESRaw -> "election.json"
  | ESKeys -> "public_keys.jsons"
  | ESCreds -> "public_creds.txt"
  | ESBallots -> "ballots.jsons"
  | ESRecords -> "records"
  | ESETally -> "encrypted_tally.json"

let election_file = Eliom_parameter.user_type
  ~of_string:election_file_of_string
  ~to_string:string_of_election_file

let uuid_of_string x =
  match Uuidm.of_string x with
  | Some x -> x
  | None -> Printf.ksprintf invalid_arg "invalid UUID [%s]" x

let uuid =
  let of_string x = uuid_of_string x
  and to_string x = Uuidm.to_string x
  in Eliom_parameter.user_type ~of_string ~to_string

type setup_election = {
  mutable se_owner : user;
  mutable se_group : string;
  mutable se_questions : template;
  mutable se_public_keys : (string * string ref) list;
  mutable se_metadata : metadata;
  mutable se_public_creds : string;
}

let b58_digits = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
let token_length = 14
let prng = lazy (pseudo_rng (random_string secure_rng 16))

let random_char () =
  lwt rng =
    if Lazy.is_val prng then return (Lazy.force prng) else
    Lwt_preemptive.detach (fun () -> Lazy.force prng) ()
  in
  return (int_of_char (random_string rng 1).[0])

let generate_token () =
  let res = String.create token_length in
  let rec loop i =
    if i < token_length then (
      lwt digit = random_char () in
      let digit = digit mod 58 in
      res.[i] <- b58_digits.[digit];
      loop (i+1)
    ) else return res
  in loop 0

let string_of_user {user_domain; user_name} =
  user_domain ^ ":" ^ user_name
